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


def test_underscore_until_end_of_line_body_paragraph():
    import form_fields as ff
    doc = Document()
    p = doc.add_paragraph("Work Order:")
    ff.underscore_until_end_of_line(p)

    check(p.text == "Work Order:\t", "label kept, followed by a tab character")
    tab_stops = p.paragraph_format.tab_stops
    check(len(tab_stops) == 1, f"exactly one tab stop added, found {len(tab_stops)}")
    if len(tab_stops) == 1:
        from docx.enum.text import WD_TAB_ALIGNMENT
        check(tab_stops[0].alignment == WD_TAB_ALIGNMENT.RIGHT, "tab stop is right-aligned")
        section = doc.sections[0]
        available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches
        check(
            abs(tab_stops[0].position.inches - available_width) < 0.01,
            f"tab stop positioned at the page's available content width ({available_width}in), got {tab_stops[0].position.inches}in",
        )


def test_underscore_until_end_of_line_in_table_cell():
    import form_fields as ff
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.columns[0].width = Inches(2.0)
    cell = table.rows[0].cells[0]
    cell.width = Inches(2.0)
    p = cell.paragraphs[0]
    p.text = "Technician:"
    ff.underscore_until_end_of_line(p)

    tab_stops = p.paragraph_format.tab_stops
    check(len(tab_stops) == 1, f"exactly one tab stop added inside a table cell, found {len(tab_stops)}")
    if len(tab_stops) == 1:
        check(
            abs(tab_stops[0].position.inches - 2.0) < 0.05,
            f"tab stop positioned at the enclosing cell's width (2.0in), got {tab_stops[0].position.inches}in",
        )


def test_apply_form_fields_marker():
    import form_fields as ff
    doc = Document()
    doc.add_paragraph("@@@FORM_FIELD:FillLine@@@Work Order:@@@END_FORM_FIELD@@@")
    temp_path = TEST_OUTPUT_DIR / "form_fields_marker.docx"
    doc.save(temp_path)

    ff.apply_form_fields(temp_path)

    result_doc = Document(temp_path)
    check(len(result_doc.paragraphs) == 1, "marker paragraph is reused (not duplicated)")
    check(result_doc.paragraphs[0].text == "Work Order:\t", f"marker replaced with label + tab, got {result_doc.paragraphs[0].text!r}")
    check("@@@" not in result_doc.paragraphs[0].text, "no marker text remains")


def test_apply_form_fields_marker_in_table_cell():
    import form_fields as ff
    doc = Document()
    table = doc.add_table(rows=1, cols=1)
    table.columns[0].width = Inches(2.0)
    cell = table.rows[0].cells[0]
    cell.width = Inches(2.0)
    cell.paragraphs[0].text = "@@@FORM_FIELD:FillLine@@@WO#@@@END_FORM_FIELD@@@"
    temp_path = TEST_OUTPUT_DIR / "form_fields_marker_in_cell.docx"
    doc.save(temp_path)

    ff.apply_form_fields(temp_path)

    result_doc = Document(temp_path)
    cell_text = result_doc.tables[0].rows[0].cells[0].text
    check("@@@" not in cell_text, "no marker text remains inside the table cell")
    check(cell_text == "WO#\t", f"marker replaced with label + tab inside a table cell, got {cell_text!r}")


def test_no_shebang_in_form_compiler_scripts():
    def has_shebang(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        return bool(lines) and lines[0].startswith("#!")

    offenders = [str(p) for p in SHEBANG_GUARDED_SCRIPTS if has_shebang(p)]
    check(not offenders, f"no shebang lines in guarded form-compiler scripts (offenders: {offenders})")


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
    test_underscore_until_end_of_line_body_paragraph()
    test_underscore_until_end_of_line_in_table_cell()
    test_apply_form_fields_marker()
    test_apply_form_fields_marker_in_table_cell()
    test_no_shebang_in_form_compiler_scripts()
    test_check_deps_runs_and_reports()

    print(f"\n{passed} passed, {failed} failed (dilon-document-form-compiler)")
    if failed == 0:
        print("\nAll form-compiler tests passed!")
        return 0
    print("\nSome form-compiler tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
