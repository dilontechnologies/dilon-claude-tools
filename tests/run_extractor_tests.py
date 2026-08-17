"""
Test suite for the dilon-document-extractor skill.

Direct-invocation style, matching tests/run_tests.py: a global
passed/failed counter via check(), explicit test calls from main(), no
pytest.
"""

import subprocess
import sys
from pathlib import Path

import yaml
from docx import Document
from docx.shared import Inches

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


def _add_table(doc, rows):
    """rows: list of list[str]. Returns the created docx.table.Table."""
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            table.rows[r].cells[c].text = text
    return table


def test_classify_table_signature():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [
        ["Group", "Preparer", "Signature"],
        ["Engineering", "P. Gray", "Electronic"],
        ["Department", "Name", "Signature"],
        ["Regulatory", "Pedro Cruz", "Electronic"],
        ["Quality", "Rebecca Miller", "Electronic"],
        ["Engineering", "Kevin Lint", "Electronic"],
    ])
    check(ex.classify_table(table) == "signature", "canonical signature-approval table is classified as 'signature'")


def test_classify_table_revision():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Initial release", "ECO-000046", "4 Mar 2025"],
    ])
    check(ex.classify_table(table) == "revision", "revision-history table is classified as 'revision'")


def test_classify_table_content():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["Setting", "Value"], ["Pressure", "75 psi"]])
    check(ex.classify_table(table) == "content", "an ordinary data table is classified as 'content'")


def test_extract_signature_fields_clean_labels():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [
        ["Group", "Preparer", "Signature"],
        ["Engineering", "P. Gray", "Electronic"],
        ["Department", "Name", "Signature"],
        ["Regulatory", "Pedro Cruz", "Electronic"],
        ["Quality", "Rebecca Miller", "Electronic"],
        ["Engineering", "Kevin Lint", "Electronic"],
    ])
    fields, warnings = ex.extract_signature_fields(table)
    check(fields["author"] == "P. Gray", "author extracted from row 1")
    check(fields["department"] == "Engineering", "department extracted from row 1")
    check(fields["regulatory_rep"] == "Pedro Cruz", "regulatory_rep extracted by position")
    check(fields["quality_rep"] == "Rebecca Miller", "quality_rep extracted by position")
    check(fields["department_head"] == "Kevin Lint", "department_head extracted by position")
    check(warnings == [], "no warnings when every row label matches its canonical role")


def test_extract_signature_fields_mismatched_labels_warns():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [
        ["Group", "Preparer", "Signature"],
        ["Engineering", "P. Gray", "Electronic"],
        ["Department", "Name", "Signature"],
        ["R&D / Eng", "K. Lint", "Electronic"],
        ["Manufacturing", "J. Jones", "Electronic"],
        ["Quality", "K. Mack", "Electronic"],
    ])
    fields, warnings = ex.extract_signature_fields(table)
    check(fields["regulatory_rep"] == "K. Lint", "regulatory_rep still assigned by position despite label mismatch")
    check(len(warnings) == 3, f"a warning is emitted for each of the 3 mismatched role labels, got {len(warnings)}")


def test_extract_revisions():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Original product transfer to Dilon Manufacturing", "ECO-000046", "4 Mar 2025"],
    ])
    revisions = ex.extract_revisions(table)
    check(len(revisions) == 1, "one revision row extracted")
    check(revisions[0]["number"] == "00", "revision number extracted")
    check(revisions[0]["eco_number"] == "ECO-000046", "eco_number extracted")


def test_extract_header_footer_metadata():
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nNav 3, Detector Head Assembly"
    header_table.rows[0].cells[2].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:\nWI-00077"
    section.footer.paragraphs[0].text = "WI-00077 Rev 00\tECO-000046\tRevision Date: 03/4/2025"

    fields = ex.extract_header_footer_metadata(doc)
    check(fields.get("doc_number") == "WI-00077", f"doc_number parsed from header/footer, got {fields.get('doc_number')!r}")
    check(fields.get("current_revision") == "00", f"current_revision parsed, got {fields.get('current_revision')!r}")


def test_strip_figure_prefix():
    import extract_docx as ex
    check(
        ex.strip_figure_prefix("Figure 1: Crystal Ends (Polished on Left)") == "Crystal Ends (Polished on Left)",
        "colon-style figure prefix stripped",
    )
    check(
        ex.strip_figure_prefix("Figure 12.3 - Compressor Gauges") == "Compressor Gauges",
        "dash-style figure prefix with a decimal number stripped",
    )
    check(ex.strip_figure_prefix("Just a caption") == "Just a caption", "text with no prefix is unchanged")


def test_slugify_dedup():
    import extract_docx as ex
    seen = set()
    check(ex.slugify("Crystal Ring", seen) == "crystal-ring", "basic slugify")
    check(ex.slugify("Crystal Ring", seen) == "crystal-ring-2", "second collision gets a -2 suffix")
    check(ex.slugify("Crystal Ring", seen) == "crystal-ring-3", "third collision gets a -3 suffix")


def _build_fixture_docx(path):
    """Builds a small synthetic .docx exercising every extraction path at
    once: header/footer metadata, a signature table with one mismatched
    role label, a revision table, two heading levels, an inline image with
    an adjacent Caption paragraph, a List Paragraph run, and a plain
    content table. Mirrors WI-00077's structure at a scale small enough to
    hand-verify in a test."""
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=3, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nFixture Document"
    header_table.rows[0].cells[2].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:\nWI-99999"
    section.footer.paragraphs[0].text = "WI-99999 Rev 00\tECO-000099\tRevision Date: 1/1/2026"

    doc.add_paragraph("Preparation", style="Heading 1")
    doc.add_paragraph("Clean the parts before assembly.", style="Normal")
    p1 = doc.add_paragraph("Wear clean gloves.", style="List Paragraph")
    p2 = doc.add_paragraph("Blow away loose dust.", style="List Paragraph")

    image_path = Path(__file__).parent / "extractor-test-output" / "_fixture_image.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    # 1x1 transparent PNG, smallest valid image payload
    image_path.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c49444154789c63f8ffff3f0005fe02fe0def46b8000000004945"
        "4e44ae426082"
    ))
    doc.add_picture(str(image_path))
    doc.add_paragraph("Figure 1: Crystal Ends (Polished on Left)", style="Caption")

    doc.add_paragraph("Bonding", style="Heading 1")
    doc.add_paragraph("Apply epoxy to the crystal.", style="Normal")

    _add_table(doc, [["Setting", "Value"], ["Pressure", "75 psi"]])

    _add_table(doc, [
        ["Group", "Preparer", "Signature"],
        ["Engineering", "P. Gray", "Electronic"],
        ["Department", "Name", "Signature"],
        ["R&D / Eng", "K. Lint", "Electronic"],
        ["Manufacturing", "J. Jones", "Electronic"],
        ["Quality", "K. Mack", "Electronic"],
    ])

    _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Initial release", "ECO-000099", "1 Jan 2026"],
    ])

    doc.save(str(path))


def test_extract_full_fixture():
    import extract_docx as ex
    fixture_path = TEST_OUTPUT_DIR / "fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "fixture-extracted"
    _build_fixture_docx(fixture_path)

    result = ex.extract(fixture_path, output_dir)

    check(result["markdown_path"].exists(), "extract() writes a markdown file")
    content = result["markdown_path"].read_text(encoding="utf-8")

    front_matter_text = content.split("---\n")[1]
    front_matter = yaml.safe_load(front_matter_text)

    check(front_matter["doc_number"] == "WI-99999", f"doc_number in front matter, got {front_matter.get('doc_number')!r}")
    check(front_matter["author"] == "P. Gray", f"author in front matter, got {front_matter.get('author')!r}")
    check(front_matter["quality_rep"] == "J. Jones", f"quality_rep assigned by position, got {front_matter.get('quality_rep')!r}")
    check(front_matter["revisions"][0]["eco_number"] == "ECO-000099", "revisions list populated from body table")

    check("Group | Preparer | Signature" not in content, "signature table text excluded from body")
    check("REVISION HISTORY" not in content, "revision table text excluded from body")
    check("## Preparation" in content, "Heading 1 shifted to markdown H2")
    check("## Bonding" in content, "second Heading 1 also shifted to markdown H2")
    check("- Wear clean gloves." in content, "List Paragraph converted to a markdown bullet")
    check("![Crystal Ends (Polished on Left)]" in content, "figure prefix stripped, remaining caption used as alt text")
    check("{#fig:crystal-ends-polished-on-left}" in content, "figure gets a slugified id")
    check("<!-- EXTRACTOR:" in content, "at least one review comment present (mismatched signature-role labels)")

    images = list(result["images_dir"].glob("*"))
    check(len(images) == 1, f"one image extracted, got {len(images)}")


def test_table_to_markdown_pipe():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["A", "B"], ["1", "2"]])
    md = ex.table_to_markdown(table)
    check(md.splitlines()[0] == "| A | B |", "pipe table header row rendered")
    check("---" in md.splitlines()[1], "pipe table separator row rendered")


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
    test_classify_table_signature()
    test_classify_table_revision()
    test_classify_table_content()
    test_extract_signature_fields_clean_labels()
    test_extract_signature_fields_mismatched_labels_warns()
    test_extract_revisions()
    test_extract_header_footer_metadata()
    test_strip_figure_prefix()
    test_slugify_dedup()
    test_extract_full_fixture()
    test_table_to_markdown_pipe()

    print(f"\n{passed} passed, {failed} failed (dilon-document-extractor)")
    if failed == 0:
        print("\nAll extractor tests passed!")
        return 0
    print("\nSome extractor tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
