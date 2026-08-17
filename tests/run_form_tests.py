"""
Test suite for the dilon-document-form-compiler skill.

Direct-invocation style, matching tests/run_tests.py: a global
passed/failed counter via check(), explicit test calls from main(), no
pytest.
"""

import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.shared import Inches

REPO_ROOT = Path(__file__).parent.parent
FORM_COMPILER_DIR = REPO_ROOT / "skills" / "dilon-document-form-compiler"
SCRIPTS_DIR = FORM_COMPILER_DIR / "scripts"
# Shared with dilon-document-compiler - both skills use the same
# header/footer/styles-only base template, no form-specific copy.
BASE_TEMPLATE = REPO_ROOT / "templates" / "TEMPLATE_Word_Base.docx"
CHECK_DEPS_SCRIPT = SCRIPTS_DIR / "check_deps.py"
FORM_COMPILER_SCRIPT = SCRIPTS_DIR / "generate_dilon_form.py"
TEST_OUTPUT_DIR = Path(__file__).parent / "form-test-output"

SHEBANG_GUARDED_SCRIPTS = [
    CHECK_DEPS_SCRIPT,
    FORM_COMPILER_SCRIPT,
    SCRIPTS_DIR / "form_fields.py",
    Path(__file__),
]

sys.path.insert(0, str(SCRIPTS_DIR))

passed = 0
failed = 0


def check(condition, message):
    global passed, failed
    if condition:
        print(f"[PASS] {message}")
        passed += 1
    else:
        print(f"[FAIL] {message}")
        failed += 1


SAMPLE_FORM_MARKDOWN = (
    '---\n'
    'title: "Detector Head Assy Traveler"\n'
    'author: "Test Suite"\n'
    'department: "Engineering"\n'
    'doc_number: "FO-99999"\n'
    'current_revision: "00"\n'
    'regulatory_rep: "Test Rep"\n'
    'quality_rep: "Test QA"\n'
    'department_head: "Test Head"\n'
    'revisions:\n'
    '  - number: "00"\n'
    '    description: "Initial test"\n'
    '    eco_number: "ECO-000"\n'
    '    eco_date: "2025-01-01"\n'
    '---\n'
    '\n'
    '| Position | Serial Number |\n'
    '|----------|----------------|\n'
    '| 1        |                |\n'
    '| 2        |                |\n'
)


def test_generate_form_document():
    input_md = TEST_OUTPUT_DIR / "form_test.md"
    output_docx = TEST_OUTPUT_DIR / "form_test.docx"
    input_md.write_text(SAMPLE_FORM_MARKDOWN, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(FORM_COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
            str(BASE_TEMPLATE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "form compiler exits 0 for a valid form document")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    check(output_docx.exists(), "form_test.docx created on disk")

    doc = Document(output_docx)
    section = doc.sections[0]
    header_text = " ".join(
        cell.text for table in section.header.tables for row in table.rows for cell in row.cells
    )
    check("Detector Head Assy Traveler" in header_text, "header title rendered (not literal {{title}})")
    check("FO-99999" in header_text, "header doc_number rendered")
    check("{{" not in header_text, "no unrendered Jinja2 braces remain in the header")

    body_tables = [t for t in doc.tables if any("Position" in c.text for c in t.rows[0].cells)]
    check(len(body_tables) == 1, "the form's own content table (Position/Serial Number) is present")
    if body_tables:
        check(body_tables[0].style.name == "DilonTable_List", "content table gets DilonTable_List styling")

    check(len(doc.tables) < 2 or not any(
        "Preparer" in c.text for t in doc.tables for row in t.rows for c in row.cells
    ), "no signature-approval table present in the compiled form")

    # No TOC: a TOC would normally be its own paragraphs/fields near the
    # top of Part D. With no headings in the form markdown, Pandoc's --toc
    # produces no TOC content either way, but confirm no 'Table of
    # Contents' heading text was emitted (would be a stray heading if TOC
    # generation were still forced on for a form).
    check(
        not any("Table of Contents" in p.text for p in doc.paragraphs),
        "no table of contents in the compiled form",
    )


def test_check_deps_runs_and_reports():
    result = subprocess.run(
        [sys.executable, str(CHECK_DEPS_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "check_deps.py exits 0 when dependencies are installed")
    check("pandoc" in result.stdout.lower(), "check_deps.py reports on pandoc")
    check("jinja2" in result.stdout.lower(), "check_deps.py reports on the jinja2 module")


def main():
    if TEST_OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

    test_generate_form_document()
    test_check_deps_runs_and_reports()

    print(f"\n{passed} passed, {failed} failed (dilon-document-form-compiler)")
    if failed == 0:
        print("\nAll form-compiler tests passed!")
        return 0
    print("\nSome form-compiler tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
