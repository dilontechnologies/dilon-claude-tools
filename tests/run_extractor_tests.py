"""
Test suite for the dilon-document-extractor skill.

Direct-invocation style, matching tests/run_tests.py: a global
passed/failed counter via check(), explicit test calls from main(), no
pytest.
"""

import subprocess
import sys
from pathlib import Path

from docx import Document

REPO_ROOT = Path(__file__).parent.parent
EXTRACTOR_DIR = REPO_ROOT / "skills" / "dilon-document-extractor"
SCRIPTS_DIR = EXTRACTOR_DIR / "scripts"
CHECK_DEPS_SCRIPT = SCRIPTS_DIR / "check_deps.py"
EXTRACT_DOCX_SCRIPT = SCRIPTS_DIR / "extract_docx.py"
EXTRACT_PDF_SCRIPT = SCRIPTS_DIR / "extract_pdf.py"
TEST_OUTPUT_DIR = Path(__file__).parent / "extractor-test-output"

SHEBANG_GUARDED_SCRIPTS = [
    CHECK_DEPS_SCRIPT,
    EXTRACT_DOCX_SCRIPT,
    EXTRACT_PDF_SCRIPT,
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


def test_check_deps_runs_and_reports():
    result = subprocess.run(
        [sys.executable, str(CHECK_DEPS_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "check_deps.py exits 0 when python-docx/pyyaml/pymupdf are installed")
    check("docx" in result.stdout, "check_deps.py reports on the docx module")
    check("yaml" in result.stdout, "check_deps.py reports on the yaml module")
    check("fitz" in result.stdout, "check_deps.py reports on the fitz (pymupdf) module")


def _doc_with_paragraphs(style_texts):
    """style_texts: list of (style_name_or_None, text). Returns an
    in-memory docx.Document with one paragraph per entry."""
    doc = Document()
    for style_name, text in style_texts:
        p = doc.add_paragraph(text)
        if style_name:
            p.style = doc.styles[style_name]
    return doc


def test_word_heading_level():
    import extract_docx as ex
    check(ex.word_heading_level("Heading 1") == 1, "Heading 1 -> level 1")
    check(ex.word_heading_level("Heading 3") == 3, "Heading 3 -> level 3")
    check(ex.word_heading_level("Normal") is None, "Normal -> no heading level")
    check(ex.word_heading_level(None) is None, "None style -> no heading level")


def test_compute_heading_shift_shallowest_becomes_h2():
    import extract_docx as ex
    doc = _doc_with_paragraphs([
        ("Heading 1", "Top Section"),
        ("Heading 2", "Sub Section"),
        ("Normal", "Body text."),
    ])
    check(ex.compute_heading_shift(doc) == 1, "shallowest Word level 1 shifts by +1 (1->## is level 2)")


def test_compute_heading_shift_no_headings_defaults_to_two():
    import extract_docx as ex
    doc = _doc_with_paragraphs([("Normal", "Just a paragraph.")])
    check(ex.compute_heading_shift(doc) == 2, "no headings present -> shift defaults to 2")


def test_markdown_heading_prefix():
    import extract_docx as ex
    check(ex.markdown_heading_prefix(1, 1) == "##", "level 1 + shift 1 -> ##")
    check(ex.markdown_heading_prefix(2, 1) == "###", "level 2 + shift 1 -> ###")
    check(ex.markdown_heading_prefix(1, 0) == "##", "level 1 + shift 0 clamps to a minimum of ##")


def test_is_suspicious_heading_text():
    import extract_docx as ex
    check(
        ex.is_suspicious_heading_text("Strong pressure on the Photomultiplier should be avoided."),
        "long sentence ending in a period is flagged as a suspicious heading",
    )
    check(not ex.is_suspicious_heading_text("Bonding"), "short title-case heading is not flagged")


def main():
    if TEST_OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

    test_check_deps_runs_and_reports()
    test_word_heading_level()
    test_compute_heading_shift_shallowest_becomes_h2()
    test_compute_heading_shift_no_headings_defaults_to_two()
    test_markdown_heading_prefix()
    test_is_suspicious_heading_text()

    print(f"\n{passed} passed, {failed} failed (dilon-document-extractor)")
    if failed == 0:
        print("\nAll extractor tests passed!")
        return 0
    print("\nSome extractor tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
