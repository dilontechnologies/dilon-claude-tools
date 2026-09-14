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
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from docx.oxml.ns import qn
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


def test_heading_is_empty_leaf():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Next Step", style="Heading 2")
    doc.add_paragraph("Detector Head Testing following FTP-00001", style="Heading 3")
    blocks = list(ex.iter_block_items(doc))

    check(
        ex.heading_is_empty_leaf(blocks, 0, 2) is False,
        "a heading followed by a deeper child heading is not an empty leaf",
    )
    check(
        ex.heading_is_empty_leaf(blocks, 1, 3) is True,
        "sole child heading with no content, followed by end of document, is an empty leaf",
    )

    doc2 = Document()
    doc2.add_paragraph("Next Step", style="Heading 2")
    doc2.add_paragraph("Detector Head Testing following FTP-00001", style="Heading 3")
    doc2.add_paragraph("See the referenced procedure for full test steps.", style="Normal")
    blocks2 = list(ex.iter_block_items(doc2))
    check(
        ex.heading_is_empty_leaf(blocks2, 1, 3) is False,
        "a child heading followed by real body content is not an empty leaf",
    )

    doc3 = Document()
    doc3.add_paragraph("Section A", style="Heading 2")
    doc3.add_paragraph("Section B", style="Heading 2")
    blocks3 = list(ex.iter_block_items(doc3))
    check(
        ex.heading_is_empty_leaf(blocks3, 0, 2) is False,
        "a sibling heading (same level, not a parent/child pair) does not trigger the empty-leaf rule",
    )

    doc4 = Document()
    doc4.add_paragraph("Next Step", style="Heading 2")
    doc4.add_paragraph("Detector Head Testing following FTP-00001", style="Heading 3")
    image_path = TEST_OUTPUT_DIR / "_leaf_fixture_image.png"
    image_path.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c49444154789c63f8ffff3f0005fe02fe0def46b8000000004945"
        "4e44ae426082"
    ))
    doc4.add_picture(str(image_path))
    blocks4 = list(ex.iter_block_items(doc4))
    check(
        ex.heading_is_empty_leaf(blocks4, 1, 3) is False,
        "a heading whose only content is an embedded image (no caption text) is not an empty leaf",
    )


def test_build_markdown_body_empty_leaf_heading_becomes_bullet():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Next Step", style="Heading 2")
    doc.add_paragraph("Detector Head Testing following FTP-00001", style="Heading 3")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("### Next Step" in body, "genuine parent heading with a child is left as a heading")
    check("#### Detector Head Testing" not in body, "childless leaf heading is not rendered as a markdown heading")
    check("- Detector Head Testing following FTP-00001" in body, "childless leaf heading rendered as a bullet instead")


def test_titlecase_heading():
    import extract_docx as ex
    check(ex.titlecase_heading("RESPONSIBILITIES") == "Responsibilities", "all-caps heading title-cased")
    check(
        ex.titlecase_heading("carrier board assembly PROCEDURE") == "Carrier Board Assembly Procedure",
        "mixed-case heading title-cased",
    )
    check(
        ex.titlecase_heading("EQUIPMENT and SUPPLIES") == "Equipment And Supplies",
        "every word's first letter is capitalized, including short words",
    )
    check(ex.titlecase_heading("PN 820-00006") == "Pn 820-00006", "digits/hyphens left untouched")


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
        ["Engineering", "Kevin Lint", "Electronic"],
        ["Regulatory", "Pedro Cruz", "Electronic"],
        ["Quality", "Rebecca Miller", "Electronic"],
    ])
    fields, warnings = ex.extract_signature_fields(table)
    check(fields["author"] == "P. Gray", "author extracted from row 1")
    check(fields["department"] == "Engineering", "department extracted from row 1")
    check(fields["department_head"] == "Kevin Lint", "department_head extracted by position")
    check(
        fields["signature_fields"] == [
            {"department": "Regulatory", "name": "Pedro Cruz"},
            {"department": "Quality", "name": "Rebecca Miller"},
        ],
        f"remaining rows extracted as signature_fields entries by position, got {fields['signature_fields']}",
    )
    check(warnings == [], "no warnings when the department head row's label matches the top department")


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
    check(fields["department_head"] == "K. Lint", "department_head still assigned by position despite label mismatch")
    check(len(warnings) == 1, f"a warning is emitted for the mismatched department head label, got {len(warnings)}")


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
    check(
        fields.get("title") == "Nav 3, Detector Head Assembly",
        f"title parsed from combined label+value header cell, got {fields.get('title')!r}",
    )
    check(fields.get("footer_eco_number") == "ECO-000046", f"footer_eco_number parsed, got {fields.get('footer_eco_number')!r}")
    check(fields.get("footer_eco_date") == "03/4/2025", f"footer_eco_date parsed, got {fields.get('footer_eco_date')!r}")


def test_extract_header_footer_metadata_table_footer():
    """Newer compiler output (see populate_footer() in
    lib/dilon_docx_common.py) carries the footer ID line as the first row
    of a 3-column table instead of tab-separated text in a single
    paragraph - table cell text isn't part of footer.paragraphs, so this
    must be read from section.footer.tables instead."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    footer_table = section.footer.add_table(rows=2, cols=3, width=Inches(6))
    footer_table.rows[0].cells[0].text = "WI-00077 Rev 00"
    footer_table.rows[0].cells[1].text = "ECO-000046"
    footer_table.rows[0].cells[2].text = "Revision Date: 03/4/2025"
    footer_table.rows[1].cells[0].text = "This document is confidential."

    fields = ex.extract_header_footer_metadata(doc)
    check(fields.get("doc_number") == "WI-00077", f"doc_number parsed from table-based footer, got {fields.get('doc_number')!r}")
    check(fields.get("current_revision") == "00", f"current_revision parsed from table-based footer, got {fields.get('current_revision')!r}")
    check(fields.get("footer_eco_number") == "ECO-000046", f"footer_eco_number parsed from table-based footer, got {fields.get('footer_eco_number')!r}")
    check(fields.get("footer_eco_date") == "03/4/2025", f"footer_eco_date parsed from table-based footer, got {fields.get('footer_eco_date')!r}")


def test_extract_header_footer_metadata_split_cells():
    """Real Dilon documents (e.g. WI-00077) split each header row's label
    and value into separate table cells rather than combining them with a
    newline in one cell."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:"
    header_table.rows[0].cells[2].text = "Nav 3, Detector Head Assembly\n PN 820-00006"
    header_table.rows[0].cells[3].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:"
    header_table.rows[1].cells[2].text = "WI-00077"

    fields = ex.extract_header_footer_metadata(doc)
    check(
        fields.get("title") == "Nav 3, Detector Head Assembly PN 820-00006",
        f"title parsed across split label/value cells, got {fields.get('title')!r}",
    )
    check(fields.get("doc_number") == "WI-00077", f"doc_number still parsed when split across cells, got {fields.get('doc_number')!r}")


def test_extract_header_footer_metadata_title_excludes_embedded_number_label():
    """Regression test for real PL-00004-01: its header combines 'Title:'
    and 'Number:' in a single table cell, separated only by a newline
    ('Title: Process Qualification ...\nNumber: PL-00004-01'), unlike
    WI-00077's separate-row layout. HEADER_LABEL_VALUE_RE's DOTALL value
    capture previously swallowed the embedded 'Number: PL-00004-01' line
    whole, producing a title literally ending in 'Number: PL-00004-01'."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=1, cols=3, width=Inches(6))
    header_table.rows[0].cells[0].text = (
        "Title: Process Qualification of Nav3 Detector Head Assy and Alignment Fixture\n"
        "Number: PL-00004-01"
    )
    header_table.rows[0].cells[1].text = "Rev 00"

    fields = ex.extract_header_footer_metadata(doc)
    check(
        fields.get("title") == "Process Qualification of Nav3 Detector Head Assy and Alignment Fixture",
        f"title excludes the embedded 'Number: ...' line, got {fields.get('title')!r}",
    )
    check(
        fields.get("doc_number") == "PL-00004-01",
        f"doc_number still parsed correctly from the same combined cell, got {fields.get('doc_number')!r}",
    )


def test_truncate_at_embedded_header_label_leaves_genuine_multiline_value_untouched():
    import extract_docx as ex
    value = "Nav 3, Detector Head Assembly\n PN 820-00006"
    check(
        ex.truncate_at_embedded_header_label(value) == value,
        "a second line with no 'Label:' pattern (just more title text) is left untouched",
    )


def test_extract_header_footer_metadata_prototype_revision():
    """Prototype revision numbers like "02-A" (major number + alphabetic
    prototype suffix) aren't digit-only, so the header/footer Rev
    patterns must capture the full value instead of stopping at the
    leading digits."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nNav 3, Detector Head Assembly"
    header_table.rows[0].cells[2].text = "Rev 02-A"
    header_table.rows[1].cells[1].text = "Number:\nWI-00077"
    section.footer.paragraphs[0].text = "WI-00077 Rev 02-A\tECO-000046\tRevision Date: 03/4/2025"

    fields = ex.extract_header_footer_metadata(doc)
    check(fields.get("current_revision") == "02-A", f"prototype current_revision parsed in full, got {fields.get('current_revision')!r}")
    check(fields.get("footer_eco_number") == "ECO-000046", f"footer_eco_number still parsed alongside a prototype revision, got {fields.get('footer_eco_number')!r}")
    check(fields.get("footer_eco_date") == "03/4/2025", f"footer_eco_date still parsed alongside a prototype revision, got {fields.get('footer_eco_date')!r}")


def test_extract_header_footer_metadata_iso_footer_date():
    """An ISO-format footer date (YYYY-MM-DD, as real newer Dilon documents
    use) must be captured in full - a date pattern that only accepts digits
    and '/' would truncate '2026-08-31' to '2026' at the first hyphen."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nNav 3, Detector Head Assembly"
    header_table.rows[0].cells[2].text = "Rev 01-A"
    header_table.rows[1].cells[1].text = "Number:\nWI-00077"
    section.footer.paragraphs[0].text = "WI-00077 Rev 01-A\tECO-000262\tRevision Date: 2026-08-31"

    fields = ex.extract_header_footer_metadata(doc)
    check(
        fields.get("footer_eco_date") == "2026-08-31",
        f"ISO-format footer_eco_date parsed in full, got {fields.get('footer_eco_date')!r}",
    )


def test_extract_header_footer_metadata_doc_number_part_suffix():
    """Some Dilon doc numbers carry a trailing part-number suffix beyond
    the first digit run (real PL-00004-01 is its own distinct Arena item
    number, not 'PL-00004' at some revision '01') - the header doc-number
    pattern must capture the full value instead of stopping at the first
    '-digits' group, the same class of bug the prototype-revision and
    ISO-date fixes above already cover for their own fields."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "Title:\nProcess Qualification Fixture"
    header_table.rows[0].cells[2].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:\nPL-00004-01"

    fields = ex.extract_header_footer_metadata(doc)
    check(
        fields.get("doc_number") == "PL-00004-01",
        f"doc_number with a part-number suffix parsed in full from the header, got {fields.get('doc_number')!r}",
    )


def test_extract_header_footer_metadata_footer_doc_number_part_suffix():
    """Same part-suffix fix as above, but exercised via the footer-line
    pattern specifically (no header 'Number:' cell present, so
    extract_header_footer_metadata() has only the footer to source
    doc_number from) - FOOTER_LINE_RE's doc-number capture group needed
    the identical fix, not just DOC_NUMBER_RE's."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    section.footer.paragraphs[0].text = "PL-00004-01 Rev 00\tECO-000262\tRevision Date: 2026-09-01"

    fields = ex.extract_header_footer_metadata(doc)
    check(
        fields.get("doc_number") == "PL-00004-01",
        f"doc_number with a part-number suffix parsed in full from the footer, got {fields.get('doc_number')!r}",
    )


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


def _add_direct_numpr(paragraph, ilvl=0):
    """Attach direct (non-style-based) w:numPr list formatting to a
    paragraph, mirroring real Dilon documents where some list items are
    left 'Normal'-styled with manual list formatting instead of the 'List
    Paragraph' style."""
    pPr = paragraph._p.get_or_add_pPr()
    numPr = pPr.makeelement(qn('w:numPr'), {})
    ilvl_el = numPr.makeelement(qn('w:ilvl'), {})
    ilvl_el.set(qn('w:val'), str(ilvl))
    numId = numPr.makeelement(qn('w:numId'), {})
    numId.set(qn('w:val'), '1')
    numPr.append(ilvl_el)
    numPr.append(numId)
    pPr.append(numPr)


def _add_field_char_run(paragraph, fld_char_type):
    """Append a run containing a single <w:fldChar> marker (begin/separate/
    end) to paragraph, mirroring one leg of a Word complex field."""
    run = paragraph.add_run()
    fld_char = run._r.makeelement(qn('w:fldChar'), {})
    fld_char.set(qn('w:fldCharType'), fld_char_type)
    run._r.append(fld_char)
    return run


def _add_instr_text_run(paragraph, instr):
    """Append a run containing a single <w:instrText> field-code element to
    paragraph - this is the instruction portion of a Word complex field
    (e.g. 'REF fig:some-label \\h'), never visible via Run.text."""
    run = paragraph.add_run()
    instr_el = run._r.makeelement(qn('w:instrText'), {})
    instr_el.text = instr
    run._r.append(instr_el)
    return run


def _add_complex_field(paragraph, instr, cached_text, bold=False):
    """Insert a full Word complex field (begin -> instrText -> separate ->
    cached result -> end) into paragraph, mirroring the run sequence Word
    itself emits for a cross-reference field like 'REF fig:label \\h'
    whose last-cached display result is `cached_text`."""
    _add_field_char_run(paragraph, 'begin')
    _add_instr_text_run(paragraph, instr)
    _add_field_char_run(paragraph, 'separate')
    result_run = paragraph.add_run(cached_text)
    result_run.bold = bold
    _add_field_char_run(paragraph, 'end')


def _add_fig_bookmark(paragraph, name):
    """Insert a <w:bookmarkStart>/<w:bookmarkEnd> pair (with no content
    inside, sufficient for label-detection tests) at the start of
    paragraph, mirroring how a real compiled Dilon document anchors a
    fig: bookmark around a Caption paragraph's auto-numbered prefix."""
    start = paragraph._p.makeelement(qn('w:bookmarkStart'), {})
    start.set(qn('w:name'), name)
    start.set(qn('w:id'), '1')
    end = paragraph._p.makeelement(qn('w:bookmarkEnd'), {})
    end.set(qn('w:id'), '1')
    paragraph._p.append(start)
    paragraph._p.append(end)


def test_paragraph_inline_markdown_converts_ref_fig_field_to_xref_link():
    """Regression test for real FTP-00001: a body paragraph referencing a
    figure via Word's 'Insert Cross-reference' feature stores a REF field
    to a fig: bookmark, not typed text - python-docx's Run.text only reads
    the field's stale cached digit ('1', since Figure numbering restarts
    every Heading 2 section), so every such reference read back as a bare
    '(1)' with no link back to which figure it meant. The field must be
    recognized and rewritten into a live [](#fig:label) cross-reference
    (MARKDOWN_STYLING_GUIDE.md SS9.3), not left as its cached digit."""
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("find the calibration date and strength on the Co-57 source disk (")
    _add_complex_field(p, "REF fig:figure-disk-source-calibration-date \\h", "1")
    p.add_run(").")

    check(
        ex.paragraph_inline_markdown(p) == (
            "find the calibration date and strength on the Co-57 source disk "
            "([](#fig:figure-disk-source-calibration-date))."
        ),
        f"REF fig: field rewritten to a live cross-reference link, got {ex.paragraph_inline_markdown(p)!r}",
    )


def test_paragraph_inline_markdown_leaves_unrecognized_field_as_cached_text():
    """A field that isn't a REF to a fig: bookmark (e.g. PAGE, or a REF to
    some other kind of bookmark) has no corresponding anchor syntax this
    extractor emits anywhere - rewriting it would produce a dangling
    cross-reference that fails compilation. It must fall back to its
    plain cached text, matching pre-existing behavior for every field type
    other than REF fig:."""
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("See page ")
    _add_complex_field(p, "PAGE", "3")
    p.add_run(" for details.")

    check(
        ex.paragraph_inline_markdown(p) == "See page 3 for details.",
        f"unrecognized field left as its cached text, got {ex.paragraph_inline_markdown(p)!r}",
    )


def test_paragraph_inline_markdown_ref_field_preserves_surrounding_bold():
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Warning: ").bold = True
    p.add_run("see (")
    _add_complex_field(p, "REF fig:hazard-diagram \\h", "1")
    p.add_run(").")

    check(
        ex.paragraph_inline_markdown(p) == "**Warning:** see ([](#fig:hazard-diagram)).",
        f"bold text around a REF fig: field is preserved, got {ex.paragraph_inline_markdown(p)!r}",
    )


def test_caption_bookmark_slug_found():
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph("Figure 2.1 - Disk Source Calibration Date", style="Caption")
    _add_fig_bookmark(p, "fig:figure-disk-source-calibration-date")

    check(
        ex.caption_bookmark_slug(p) == "figure-disk-source-calibration-date",
        f"fig: bookmark name (prefix stripped) returned, got {ex.caption_bookmark_slug(p)!r}",
    )


def test_caption_bookmark_slug_absent_returns_none():
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph("Figure 2.1 - Disk Source Calibration Date", style="Caption")

    check(
        ex.caption_bookmark_slug(p) is None,
        "no fig: bookmark present -> None, so the caller falls back to slugify(caption_text)",
    )


def test_build_markdown_body_caption_uses_bookmark_label_over_slugified_text():
    """Regression test: reusing the source document's own fig: bookmark
    name (rather than re-slugifying fresh from the caption's visible text)
    is what keeps a REF fig: field elsewhere in the same document (see
    test_paragraph_inline_markdown_converts_ref_fig_field_to_xref_link)
    resolving to the correct figure after re-extraction - a freshly
    slugified id has no guarantee of matching the original bookmark name
    the field code still points to."""
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Test Setup", style="Heading 2")
    image_path = TEST_OUTPUT_DIR / "_bookmark_fixture_image.png"
    image_path.write_bytes(bytes.fromhex(_ONE_PIXEL_PNG_HEX))
    doc.add_picture(str(image_path))
    caption = doc.add_paragraph("Figure 2.1 - Disk Source Calibration Date", style="Caption")
    _add_fig_bookmark(caption, "fig:figure-disk-source-calibration-date")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "{#fig:figure-disk-source-calibration-date" in body,
        f"image id taken from the source bookmark, not re-slugified from caption text, got body containing: "
        f"{[l for l in body.splitlines() if 'image01' in l]!r}",
    )
    check("#fig:disk-source-calibration-date" not in body, "freshly slugified id (missing 'figure-' prefix) not used instead")


def test_paragraph_is_list_item_direct_numpr():
    import extract_docx as ex
    doc = Document()
    p1 = doc.add_paragraph("Styled as List Paragraph")
    p1.style = doc.styles["List Paragraph"]
    p2 = doc.add_paragraph("Normal style but has direct numPr")
    _add_direct_numpr(p2)
    p3 = doc.add_paragraph("Plain Normal paragraph")

    check(ex.paragraph_is_list_item(p1) is True, "'List Paragraph'-styled paragraph detected as a list item")
    check(ex.paragraph_is_list_item(p2) is True, "Normal-styled paragraph with direct numPr formatting detected as a list item")
    check(ex.paragraph_is_list_item(p3) is False, "plain Normal paragraph is not a list item")


def test_paragraph_list_ilvl():
    import extract_docx as ex
    doc = Document()
    p0 = doc.add_paragraph("Top-level item")
    p0.style = doc.styles["List Paragraph"]
    _add_direct_numpr(p0, ilvl=0)
    p1 = doc.add_paragraph("Nested item")
    p1.style = doc.styles["List Paragraph"]
    _add_direct_numpr(p1, ilvl=1)
    p2 = doc.add_paragraph("No list formatting at all")

    check(ex.paragraph_list_ilvl(p0) == 0, "top-level list item has ilvl 0")
    check(ex.paragraph_list_ilvl(p1) == 1, "nested list item has ilvl 1")
    check(ex.paragraph_list_ilvl(p2) == 0, "non-list paragraph defaults to ilvl 0")


def test_build_markdown_body_nested_list_indentation():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Mixing Epoxy", style="Heading 2")
    top = doc.add_paragraph("The epoxy is purchased in a pre-measured packet.")
    top.style = doc.styles["List Paragraph"]
    _add_direct_numpr(top, ilvl=0)
    nested = doc.add_paragraph("Read the outer package to confirm the expiration date.")
    nested.style = doc.styles["List Paragraph"]
    _add_direct_numpr(nested, ilvl=1)

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("- The epoxy is purchased in a pre-measured packet." in body, "top-level (ilvl 0) list item rendered with no indent")
    check(
        "  - Read the outer package to confirm the expiration date." in body,
        "nested (ilvl 1) list item rendered with a 2-space indent",
    )


def test_is_toc_paragraph():
    import extract_docx as ex
    check(ex.is_toc_paragraph("toc 1", "1.\tIntroduction\t3"), "'toc 1'-styled paragraph is a TOC entry")
    check(ex.is_toc_paragraph("toc 2", "1.1\tScope\t3"), "'toc 2'-styled paragraph is a TOC entry")
    check(ex.is_toc_paragraph("Normal", "TABLE OF CONTENTS"), "literal 'TABLE OF CONTENTS' text is a TOC heading")
    check(not ex.is_toc_paragraph("Normal", "Regular body text."), "ordinary body text is not a TOC paragraph")
    check(not ex.is_toc_paragraph("Heading 1", "Introduction"), "a real heading is not a TOC paragraph")


def test_build_markdown_body_skips_toc_and_converts_direct_numpr_list():
    import extract_docx as ex
    doc = Document()
    doc.styles.add_style("toc 1", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("TABLE OF CONTENTS", style="Normal")
    doc.add_paragraph("1.\tIntroduction\t3", style="toc 1")
    doc.add_paragraph("Introduction", style="Heading 1")
    p = doc.add_paragraph("Providing support as necessary.", style="Normal")
    _add_direct_numpr(p)

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("TABLE OF CONTENTS" not in body, "literal TOC heading text excluded from body")
    check("Introduction\t3" not in body, "toc-styled entry paragraph excluded from body")
    check("## Introduction" in body, "real heading still present after TOC removal")
    check("- Providing support as necessary." in body, "Normal-styled paragraph with direct numPr rendered as a markdown bullet")


def _add_page_break(paragraph):
    paragraph.add_run().add_break(WD_BREAK.PAGE)


def test_paragraph_has_page_break():
    import extract_docx as ex
    doc = Document()
    plain = doc.add_paragraph("Ordinary text.")
    broken = doc.add_paragraph()
    _add_page_break(broken)

    check(not ex.paragraph_has_page_break(plain), "ordinary paragraph has no page break")
    check(ex.paragraph_has_page_break(broken), "paragraph with a w:br type=page run is detected")


def test_first_heading_block_index():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Not a heading.")
    doc.add_paragraph("Objective", style="Heading 2")
    doc.add_paragraph("Body text.")

    blocks = list(ex.iter_block_items(doc))
    check(ex.first_heading_block_index(blocks) == 1, "first heading found at its block index")

    doc_no_headings = Document()
    doc_no_headings.add_paragraph("Just a paragraph.")
    blocks_no_headings = list(ex.iter_block_items(doc_no_headings))
    check(ex.first_heading_block_index(blocks_no_headings) is None, "None returned when no heading exists")


def test_build_markdown_body_leading_page_break_before_first_heading_skipped():
    import extract_docx as ex
    doc = Document()
    _add_page_break(doc.add_paragraph())
    doc.add_paragraph("Objective", style="Heading 2")
    doc.add_paragraph("The purpose of this document is...")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "---" not in body,
        "a page break before the first heading (the title-page/TOC boundary) is not reproduced as '---'",
    )


def test_build_markdown_body_inbody_page_break_becomes_thematic_break():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Reporting", style="Heading 2")
    doc.add_paragraph("Execution of this Plan is recorded below.")
    _add_page_break(doc.add_paragraph())
    doc.add_paragraph("Data Recording", style="Heading 2")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("---" in body, "a page break inside the body is reproduced as a '---' thematic break")
    check(
        body.index("---") < body.index("## Data Recording") and body.index("## Reporting") < body.index("---"),
        "the '---' lands between the two headings, where the source page break actually was",
    )


def test_extract_flags_footer_revision_eco_mismatch():
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nMismatch Fixture"
    header_table.rows[0].cells[2].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:\nWI-88888"
    section.footer.paragraphs[0].text = "WI-88888 Rev 00\tECO-000123\tRevision Date: 5/5/2025"

    _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Initial release", "ECO-000999", "5 May 2025"],
    ])

    fixture_path = TEST_OUTPUT_DIR / "footer-mismatch-fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "footer-mismatch-extracted"
    doc.save(str(fixture_path))

    result = ex.extract(fixture_path, output_dir)
    content = result["markdown_path"].read_text(encoding="utf-8")
    front_matter = yaml.safe_load(content.split("---\n")[1])

    check("footer_eco_number" not in front_matter, "footer_eco_number not leaked into final front matter")
    check("footer_eco_date" not in front_matter, "footer_eco_date not leaked into final front matter")
    check(
        any("disagreement" in w.lower() for w in result["warnings"]),
        "ECO mismatch between footer and revision table produces a disagreement warning",
    )


def test_extract_no_warning_when_footer_matches_revision():
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nMatch Fixture"
    header_table.rows[0].cells[2].text = "Rev 00"
    header_table.rows[1].cells[1].text = "Number:\nWI-77777"
    section.footer.paragraphs[0].text = "WI-77777 Rev 00\tECO-000555\tRevision Date: 6/6/2025"

    _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Initial release", "ECO-000555", "6/6/2025"],
    ])

    fixture_path = TEST_OUTPUT_DIR / "footer-match-fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "footer-match-extracted"
    doc.save(str(fixture_path))

    result = ex.extract(fixture_path, output_dir)
    check(
        not any("disagreement" in w.lower() for w in result["warnings"]),
        "matching footer/revision-table ECO data produces no disagreement warning",
    )


def test_extract_current_revision_corrected_from_stale_header_suffix():
    """Regression test: a real Dilon prototype revision (e.g. '01-A') that the
    running header spells without its letter suffix (a stale/hand-typed
    header, as seen in real WI-00077/WI-00088 source documents) must not
    silently win over the revision-history table - the table's most recent
    row is the authoritative current revision."""
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nStale Header Fixture"
    header_table.rows[0].cells[2].text = "Rev 01"
    header_table.rows[1].cells[1].text = "Number:\nWI-66666"

    _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["00", "Initial release", "ECO-000046", "4 Mar 2025"],
        ["01-A", "Prototype release", "ECO-000262", "31 Aug 2026"],
    ])

    fixture_path = TEST_OUTPUT_DIR / "stale-header-revision-fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "stale-header-revision-extracted"
    doc.save(str(fixture_path))

    result = ex.extract(fixture_path, output_dir)
    content = result["markdown_path"].read_text(encoding="utf-8")
    front_matter = yaml.safe_load(content.split("---\n")[1])

    check(
        front_matter["current_revision"] == "01-A",
        f"current_revision corrected to the revision table's latest row, got {front_matter['current_revision']!r}",
    )
    check(
        any("disagrees with the revision-history table" in w for w in result["warnings"]),
        "header/table current_revision disagreement is flagged for review",
    )


def test_extract_no_warning_when_header_matches_revision_table():
    import extract_docx as ex
    doc = Document()
    section = doc.sections[0]
    header_table = section.header.add_table(rows=2, cols=4, width=Inches(6))
    header_table.rows[0].cells[1].text = "WI:\nMatching Header Fixture"
    header_table.rows[0].cells[2].text = "Rev 01-A"
    header_table.rows[1].cells[1].text = "Number:\nWI-55555"

    _add_table(doc, [
        ["REVISION HISTORY", "", "", ""],
        ["REV #", "DESCRIPTION OF CHANGE", "ECO #", "DATE"],
        ["01-A", "Prototype release", "ECO-000262", "31 Aug 2026"],
    ])

    fixture_path = TEST_OUTPUT_DIR / "matching-header-revision-fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "matching-header-revision-extracted"
    doc.save(str(fixture_path))

    result = ex.extract(fixture_path, output_dir)
    check(
        not any("disagrees with the revision-history table" in w for w in result["warnings"]),
        "matching header/revision-table current_revision produces no disagreement warning",
    )


def test_build_markdown_body_suspicious_heading_becomes_step():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Preparation", style="Heading 1")
    doc.add_paragraph("Simple dirt can be blown away.", style="List Paragraph")
    doc.add_paragraph("Strong pressure on the Photomultiplier should be avoided.", style="Heading 4")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("##### Strong pressure" not in body, "suspicious heading-styled paragraph not rendered as a markdown heading")
    check("@@@STEPS@@@" in body and "@@@END_STEPS@@@" in body, "suspicious heading-styled paragraph wrapped in a @@@STEPS@@@ block")
    check(
        "#. Strong pressure on the Photomultiplier should be avoided." in body,
        "suspicious heading-styled paragraph rendered as a step item instead",
    )
    check(any("rendered as a @@@STEPS@@@ item" in w for w in warnings), "conversion from heading to step item is flagged for review")


def test_build_markdown_body_step_run_nests_by_heading_level():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Epoxy", style="Heading 2")
    doc.add_paragraph("Mix the epoxy per the manufacturer's specs.", style="Heading 3")
    doc.add_paragraph("Use the pink needle at 10 psi.", style="Heading 4")
    doc.add_paragraph("Dispense a small amount of epoxy into a tray.", style="Heading 3")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(body.count("@@@STEPS@@@") == 1, "one contiguous step run produces a single @@@STEPS@@@ block")
    check("#. Mix the epoxy per the manufacturer's specs." in body, "first sibling step rendered at top level")
    check("  #. Use the pink needle at 10 psi." in body, "deeper heading level rendered as a nested clarification")
    check("#. Dispense a small amount of epoxy into a tray." in body, "second sibling step rendered at top level")
    check(
        not any(line.startswith("  #. Dispense") for line in body.splitlines()),
        "sibling step at the run's base level is not nested under the prior step",
    )


def test_build_markdown_body_step_run_closes_around_image():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Epoxy", style="Heading 2")
    doc.add_paragraph("Mix the epoxy per the manufacturer's specs.", style="Heading 3")
    doc.add_paragraph("A caption-less plain paragraph interrupts the run.")
    doc.add_paragraph("Dispense a small amount of epoxy into a tray.", style="Heading 3")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(body.count("@@@STEPS@@@") == 2, "an interruption closes and reopens a fresh @@@STEPS@@@ block")
    check(body.count("@@@END_STEPS@@@") == 2, "each opened @@@STEPS@@@ block is closed")


def test_build_markdown_body_dilon_step_heading_becomes_step():
    """Regression test for real WI-00077/WI-00088-style source documents:
    they were compiled by an earlier run of this same pipeline, so their
    procedure steps use this compiler's own 'Dilon Step Heading' paragraph
    style with a live STYLEREF+SEQ step-number field pair - not a Heading N
    style, not List Paragraph, no numPr list formatting. python-docx's
    .text reads a field's stale last-cached display result, not a
    recalculated value, so every step's text carries whatever number that
    cache happened to freeze on (real WI-00077's 77 steps all cache
    '1.1', regardless of actual position). Such a paragraph must be
    recognized as a step, have its stale cached number stripped, and be
    wrapped in @@@STEPS@@@ like any other procedure."""
    import extract_docx as ex
    doc = Document()
    doc.styles.add_style("Dilon Step Heading", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Mixing Epoxy", style="Heading 3")
    doc.add_paragraph("1.1\tBlend the two components of the epoxy.", style="Dilon Step Heading")
    doc.add_paragraph("1.1\tTear the outer package at the tear points.", style="Dilon Step Heading")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("@@@STEPS@@@" in body and "@@@END_STEPS@@@" in body, "'Dilon Step Heading' run wrapped in a @@@STEPS@@@ block")
    check(
        "#. Blend the two components of the epoxy." in body,
        "stale 'N.N\\t' prefix stripped, step rendered as a clean #. item",
    )
    check(
        "#. Tear the outer package at the tear points." in body,
        "second consecutive 'Dilon Step Heading' paragraph joins the same step run",
    )
    check("1.1" not in body, "no leftover stale step-number text remains anywhere in the body")


def test_strip_stale_step_number_handles_blank_cached_styleref():
    """Regression test for real WI-00088: its STYLEREF-3 field cached an
    empty result (no Heading 3 ancestor in scope when last calculated),
    so its stale prefix is bare '.\\t' rather than WI-00077's '1.1\\t' -
    both must strip cleanly since neither carries a real body-text digit."""
    import extract_docx as ex
    check(
        ex.strip_stale_step_number(".\tIf the epoxy or adhesive being used requires mixing.")
        == "If the epoxy or adhesive being used requires mixing.",
        "bare '.' + tab (blank cached STYLEREF) prefix stripped",
    )
    check(
        ex.strip_stale_step_number("1.1\tBlend the two components.") == "Blend the two components.",
        "full 'N.N' + tab prefix still stripped (no regression)",
    )
    check(
        ex.strip_stale_step_number("Plain text with no stale prefix.") == "Plain text with no stale prefix.",
        "text with no stale prefix is left untouched",
    )


def test_build_markdown_body_dilon_step_heading_run_closes_at_next_heading():
    import extract_docx as ex
    doc = Document()
    doc.styles.add_style("Dilon Step Heading", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Mixing Epoxy", style="Heading 3")
    doc.add_paragraph("1.1\tBlend the two components of the epoxy.", style="Dilon Step Heading")
    doc.add_paragraph("Bonding Crystal", style="Heading 3")
    doc.add_paragraph("1.1\tCenter the crystal over the photomultiplier.", style="Dilon Step Heading")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(body.count("@@@STEPS@@@") == 2, "a new Heading 3 closes the current step run and opens a fresh one")
    check(body.count("@@@END_STEPS@@@") == 2, "each 'Dilon Step Heading' run is properly closed")


def test_build_markdown_body_dilon_step_heading_warns_once_with_count():
    """A 'Dilon Step Heading' match is unambiguous (unlike the heuristic
    'suspicious heading' guess), and a real document can carry dozens of
    them (WI-00077 has 77) - one summary warning with the count, not one
    repeated near-identical warning per paragraph, keeps the cleanup-pass
    warning list actually readable."""
    import extract_docx as ex
    doc = Document()
    doc.styles.add_style("Dilon Step Heading", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Mixing Epoxy", style="Heading 3")
    doc.add_paragraph("1.1\tBlend the two components of the epoxy.", style="Dilon Step Heading")
    doc.add_paragraph("1.1\tTear the outer package at the tear points.", style="Dilon Step Heading")
    doc.add_paragraph("1.1\tRoll one end of the Bi-Pack.", style="Dilon Step Heading")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    step_warnings = [w for w in warnings if "Dilon Step Heading" in w]
    check(len(step_warnings) == 1, f"exactly one summary warning emitted, got {len(step_warnings)}")
    check("3" in step_warnings[0] if step_warnings else False, f"summary warning states the count, got {step_warnings}")


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


_ONE_PIXEL_PNG_HEX = (
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c49444154789c63f8ffff3f0005fe02fe0def46b8000000004945"
    "4e44ae426082"
)


def _write_one_pixel_png(path):
    path.write_bytes(bytes.fromhex(_ONE_PIXEL_PNG_HEX))


def test_paragraph_image_display_size_returns_source_extent():
    """The size an image was actually displayed at in the source Word
    document (its wp:extent) is frequently very different from its native
    pixel dimensions - real WI-00077 images are shown at ~3.5in wide in
    the document despite native sizes implying 6-9in - so this must read
    the *display* extent, not infer anything from the image file itself."""
    import extract_docx as ex
    from docx.shared import Inches

    doc = Document()
    image_path = TEST_OUTPUT_DIR / "_size_fixture_image.png"
    _write_one_pixel_png(image_path)
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(3.5), height=Inches(2.0))

    rid = ex.paragraph_image_rids(p)[0]
    width_in, height_in = ex.paragraph_image_display_size(p, rid)
    check(width_in == 3.5, f"display width read from wp:extent, got {width_in!r}")
    check(height_in == 2.0, f"display height read from wp:extent, got {height_in!r}")


def test_paragraph_image_display_size_missing_rid_returns_none():
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph("No images here.")
    width_in, height_in = ex.paragraph_image_display_size(p, "rId99")
    check((width_in, height_in) == (None, None), "no matching image returns (None, None) rather than guessing")


def test_image_size_attr_emits_width_only():
    """Only width= is emitted, never height= alongside it - Pandoc scales
    the other dimension proportionally from a width-only attribute
    (MARKDOWN_STYLING_GUIDE.md SS4.2) using the image's real aspect ratio,
    which is more faithful than independently rounding both dimensions to
    2 decimal places and risking a slightly distorted aspect ratio."""
    import extract_docx as ex
    check(ex.image_size_attr(3.5, 2.25) == " width=3.5in", f"width-only attribute emitted, got {ex.image_size_attr(3.5, 2.25)!r}")
    check(ex.image_size_attr(None, 2.25) == "", "missing width -> no attribute")
    check(ex.image_size_attr(3.5, None) == "", "missing height (extent read failed) -> no attribute, even though width is present")


def test_build_markdown_body_image_carries_source_display_size():
    import extract_docx as ex
    from docx.shared import Inches

    doc = Document()
    doc.add_paragraph("Crystal Prep", style="Heading 2")
    image_path = TEST_OUTPUT_DIR / "_body_size_fixture_image.png"
    _write_one_pixel_png(image_path)
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(3.5), height=Inches(2.25))
    doc.add_paragraph("Crystal Ends", style="Caption")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "![Crystal Ends](images/image01.png){#fig:crystal-ends width=3.5in}" in body,
        f"captioned image carries its source display width only (no height=), got body containing: "
        f"{[l for l in body.splitlines() if 'image01' in l]!r}",
    )


def test_build_markdown_body_uncaptioned_image_carries_source_display_size():
    import extract_docx as ex
    from docx.shared import Inches

    doc = Document()
    doc.add_paragraph("Crystal Prep", style="Heading 2")
    image_path = TEST_OUTPUT_DIR / "_body_size_fixture_image_2.png"
    _write_one_pixel_png(image_path)
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_picture(str(image_path), width=Inches(4.0), height=Inches(1.5))

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "![](images/image01.png){width=4.0in}" in body,
        f"uncaptioned image still carries its source display width only (no height=), got body containing: "
        f"{[l for l in body.splitlines() if 'image01' in l]!r}",
    )


def test_paragraph_inline_markdown_wraps_bold_and_italic_runs():
    """Regression test: real WI-00077/WI-00088 both end on a bold closing
    line ('Finished with construction of 820-00006' / 'Dispensing Station
    is ready for use...') that was previously silently flattened to plain
    text, since block.text concatenates every run's text with no regard
    for its bold/italic character formatting."""
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Finished with construction of 820-00006").bold = True

    check(
        ex.paragraph_inline_markdown(p) == "**Finished with construction of 820-00006**",
        f"a fully-bold paragraph is wrapped in **, got {ex.paragraph_inline_markdown(p)!r}",
    )

    doc2 = Document()
    p2 = doc2.add_paragraph()
    p2.add_run("Normal text, then ")
    r = p2.add_run("italic warning")
    r.italic = True
    p2.add_run(", then normal again.")
    check(
        ex.paragraph_inline_markdown(p2) == "Normal text, then *italic warning*, then normal again.",
        f"mixed plain/italic runs render correctly, got {ex.paragraph_inline_markdown(p2)!r}",
    )

    doc3 = Document()
    p3 = doc3.add_paragraph()
    r3 = p3.add_run("critical step")
    r3.bold = True
    r3.italic = True
    check(
        ex.paragraph_inline_markdown(p3) == "***critical step***",
        f"a bold+italic run is wrapped in ***, got {ex.paragraph_inline_markdown(p3)!r}",
    )


def test_paragraph_inline_markdown_merges_adjacent_same_style_runs():
    """A single bold phrase is frequently split across multiple runs by
    Word's spell-check/autocorrect boundaries - adjacent runs sharing the
    same bold/italic state must merge into one span, not produce
    '**a****b**'-style redundant marker pairs."""
    import extract_docx as ex
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Finished with ").bold = True
    p.add_run("construction").bold = True
    p.add_run(" of 820-00006").bold = True

    check(
        ex.paragraph_inline_markdown(p) == "**Finished with construction of 820-00006**",
        f"adjacent same-style runs merge into one span, got {ex.paragraph_inline_markdown(p)!r}",
    )


def test_build_markdown_body_plain_paragraph_preserves_bold():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Bake", style="Heading 2")
    doc.add_paragraph().add_run("Finished with construction of 820-00006").bold = True

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "**Finished with construction of 820-00006**" in body,
        f"bold plain-paragraph text survives extraction, got body containing: "
        f"{[l for l in body.splitlines() if 'Finished' in l]!r}",
    )


def test_build_markdown_body_list_item_preserves_bold():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Notes", style="Heading 2")
    p = doc.add_paragraph(style="List Paragraph")
    p.add_run("Warning: ").bold = True
    p.add_run("do not exceed 150°C.")

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check(
        "- **Warning:** do not exceed 150°C." in body,
        f"bold run inside a list item survives extraction, got body containing: "
        f"{[l for l in body.splitlines() if 'Warning' in l]!r}",
    )


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
    check(front_matter["department_head"] == "K. Lint", f"department_head assigned by position, got {front_matter.get('department_head')!r}")
    check(
        front_matter["signature_fields"] == [
            {"department": "Manufacturing", "name": "J. Jones"},
            {"department": "Quality", "name": "K. Mack"},
        ],
        f"signature_fields extracted by position, got {front_matter.get('signature_fields')!r}",
    )
    check(front_matter["revisions"][0]["eco_number"] == "ECO-000099", "revisions list populated from body table")

    check("Group | Preparer | Signature" not in content, "signature table text excluded from body")
    check("REVISION HISTORY" not in content, "revision table text excluded from body")
    check("## Preparation" in content, "Heading 1 shifted to markdown H2")
    check("## Bonding" in content, "second Heading 1 also shifted to markdown H2")
    check("- Wear clean gloves." in content, "List Paragraph converted to a markdown bullet")
    check("![Crystal Ends (Polished on Left)]" in content, "figure prefix stripped, remaining caption used as alt text")
    check("#fig:crystal-ends-polished-on-left" in content, "figure gets a slugified id")
    check("width=" in content and "height=" not in content, "figure carries its source display width only, no height=")
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


def _set_table_column_widths(table, widths_in):
    """Set explicit per-column widths (inches) on table, mirroring
    apply_table_column_widths() in lib/dilon_docx_common.py - both the
    tblGrid width (table.columns[i].width) and each cell's own width must
    be set for the value to round-trip back out through python-docx."""
    from docx.shared import Inches
    table.autofit = False
    for idx, width_in in enumerate(widths_in):
        emu = Inches(width_in)
        table.columns[idx].width = emu
        for cell in table.columns[idx].cells:
            cell.width = emu


def test_table_column_widths_in_reads_explicit_widths():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["ID", "Description", "Notes"], ["1", "a wide field", "x"]])
    _set_table_column_widths(table, [1.0, 3.5, 1.5])

    widths = ex.table_column_widths_in(table)
    check(
        widths is not None and [round(w, 2) for w in widths] == [1.0, 3.5, 1.5],
        f"explicit column widths read back in inches, got {widths!r}",
    )


def _clear_table_column_widths(table):
    """Strip the w:w width attribute from every tblGrid gridCol, mirroring
    a real Word table using 'AutoFit to Contents' that was never manually
    resized - python-docx's own add_table() always writes a generic
    default gridCol width (unlike a genuinely un-sized real document), so
    this must clear it explicitly rather than relying on add_table()'s
    default to reproduce the unset case."""
    from docx.oxml.ns import qn
    grid = table._tbl.find(qn('w:tblGrid'))
    for grid_col in grid.findall(qn('w:gridCol')):
        if qn('w:w') in grid_col.attrib:
            del grid_col.attrib[qn('w:w')]


def test_table_column_widths_in_returns_none_when_unset():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["A", "B"], ["1", "2"]])
    _clear_table_column_widths(table)

    check(
        ex.table_column_widths_in(table) is None,
        "a table with no explicit column widths set (e.g. 'AutoFit to Contents', never resized) returns None rather than guessing",
    )


def test_table_column_widths_marker_flags_unequal_widths():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["ID", "Description", "Notes"], ["1", "a wide field", "x"]])
    _set_table_column_widths(table, [1.0, 3.5, 1.5])

    check(
        ex.table_column_widths_marker(table) == "@@@TABLE_COLUMNS:1.0,3.5,1.5@@@",
        f"unequal column widths produce a TABLE_COLUMNS marker, got {ex.table_column_widths_marker(table)!r}",
    )


def test_table_column_widths_marker_none_for_equal_widths():
    """An evenly-divided table's columns don't need a marker at all - the
    compiler's own default (an even split of the available width) already
    reproduces this, so asserting it explicitly would be redundant. A
    tiny (<= COLUMN_WIDTH_EQUAL_TOLERANCE_IN) real-world jitter between
    columns meant to be equal must not trip the marker either."""
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["A", "B", "C"], ["1", "2", "3"]])
    _set_table_column_widths(table, [2.0, 2.0, 2.0])
    check(ex.table_column_widths_marker(table) is None, "exactly equal column widths produce no marker")

    doc2 = Document()
    table2 = _add_table(doc2, [["A", "B"], ["1", "2"]])
    _set_table_column_widths(table2, [2.0, 2.02])
    check(ex.table_column_widths_marker(table2) is None, "widths within tolerance of each other produce no marker")


def test_table_column_widths_marker_none_when_widths_unavailable():
    import extract_docx as ex
    doc = Document()
    table = _add_table(doc, [["A", "B"], ["1", "2"]])
    _clear_table_column_widths(table)
    check(ex.table_column_widths_marker(table) is None, "a table with unreadable widths produces no marker")


def test_build_markdown_body_content_table_gets_column_width_marker():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Specs", style="Heading 2")
    table = _add_table(doc, [["ID", "Description", "Notes"], ["1", "a wide field", "x"]])
    _set_table_column_widths(table, [1.0, 3.5, 1.5])

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    lines = body.splitlines()
    marker_idx = next((i for i, l in enumerate(lines) if l.startswith("@@@TABLE_COLUMNS:")), None)
    check(marker_idx is not None, f"TABLE_COLUMNS marker present in body, got: {lines!r}")
    check(
        marker_idx is not None and lines[marker_idx + 1] == "| ID | Description | Notes |",
        "marker line sits immediately before the pipe table, no blank line between",
    )


def test_build_markdown_body_content_table_no_marker_for_equal_widths():
    import extract_docx as ex
    doc = Document()
    doc.add_paragraph("Specs", style="Heading 2")
    table = _add_table(doc, [["A", "B"], ["1", "2"]])
    _set_table_column_widths(table, [3.0, 3.0])

    blocks = list(ex.iter_block_items(doc))
    front_matter = {"revisions": []}
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, front_matter)

    check("@@@TABLE_COLUMNS:" not in body, "no TABLE_COLUMNS marker for an evenly-divided table")


def _build_fixture_pdf(path):
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Fixture PDF Document")
    page.insert_text((72, 100), "This is a body paragraph in the fixture PDF.")
    doc.save(str(path))
    doc.close()


def test_extract_pdf_banner_and_text():
    import extract_pdf as expdf
    fixture_path = TEST_OUTPUT_DIR / "fixture.pdf"
    output_dir = TEST_OUTPUT_DIR / "fixture-pdf-extracted"
    _build_fixture_pdf(fixture_path)

    result = expdf.extract(fixture_path, output_dir)

    check(result["markdown_path"].exists(), "extract_pdf.extract() writes a markdown file")
    content = result["markdown_path"].read_text(encoding="utf-8")
    check("PDF source" in content, "PDF banner comment present at the top of the draft")
    check("Fixture PDF Document" in content, "extracted text includes page content")
    check(any("PDF source" in w for w in result["warnings"]), "the banner warning is also reported in the returned warnings list")


def test_extract_docx_cli_smoke():
    fixture_path = TEST_OUTPUT_DIR / "cli-fixture.docx"
    output_dir = TEST_OUTPUT_DIR / "cli-extracted"
    _build_fixture_docx(fixture_path)

    result = subprocess.run(
        [sys.executable, str(EXTRACT_DOCX_SCRIPT), str(fixture_path), str(output_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "extract_docx.py CLI exits 0 for a valid input")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    check(any(output_dir.glob("*.md")), "extract_docx.py CLI writes a markdown file to the output directory")


def test_no_shebang_in_extractor_scripts():
    def has_shebang(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        return bool(lines) and lines[0].startswith("#!")

    offenders = [str(p) for p in SHEBANG_GUARDED_SCRIPTS if has_shebang(p)]
    check(not offenders, f"no shebang lines in guarded extractor scripts (offenders: {offenders})")


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
    test_heading_is_empty_leaf()
    test_build_markdown_body_empty_leaf_heading_becomes_bullet()
    test_titlecase_heading()
    test_classify_table_signature()
    test_classify_table_revision()
    test_classify_table_content()
    test_extract_signature_fields_clean_labels()
    test_extract_signature_fields_mismatched_labels_warns()
    test_extract_revisions()
    test_extract_header_footer_metadata()
    test_extract_header_footer_metadata_table_footer()
    test_extract_header_footer_metadata_split_cells()
    test_extract_header_footer_metadata_title_excludes_embedded_number_label()
    test_truncate_at_embedded_header_label_leaves_genuine_multiline_value_untouched()
    test_strip_figure_prefix()
    test_paragraph_inline_markdown_converts_ref_fig_field_to_xref_link()
    test_paragraph_inline_markdown_leaves_unrecognized_field_as_cached_text()
    test_paragraph_inline_markdown_ref_field_preserves_surrounding_bold()
    test_caption_bookmark_slug_found()
    test_caption_bookmark_slug_absent_returns_none()
    test_build_markdown_body_caption_uses_bookmark_label_over_slugified_text()
    test_paragraph_is_list_item_direct_numpr()
    test_paragraph_list_ilvl()
    test_build_markdown_body_nested_list_indentation()
    test_is_toc_paragraph()
    test_build_markdown_body_skips_toc_and_converts_direct_numpr_list()
    test_paragraph_has_page_break()
    test_first_heading_block_index()
    test_build_markdown_body_leading_page_break_before_first_heading_skipped()
    test_build_markdown_body_inbody_page_break_becomes_thematic_break()
    test_build_markdown_body_suspicious_heading_becomes_step()
    test_build_markdown_body_step_run_nests_by_heading_level()
    test_build_markdown_body_step_run_closes_around_image()
    test_build_markdown_body_dilon_step_heading_becomes_step()
    test_strip_stale_step_number_handles_blank_cached_styleref()
    test_build_markdown_body_dilon_step_heading_run_closes_at_next_heading()
    test_build_markdown_body_dilon_step_heading_warns_once_with_count()
    test_extract_flags_footer_revision_eco_mismatch()
    test_extract_no_warning_when_footer_matches_revision()
    test_extract_current_revision_corrected_from_stale_header_suffix()
    test_extract_no_warning_when_header_matches_revision_table()
    test_extract_header_footer_metadata_prototype_revision()
    test_extract_header_footer_metadata_iso_footer_date()
    test_extract_header_footer_metadata_doc_number_part_suffix()
    test_extract_header_footer_metadata_footer_doc_number_part_suffix()
    test_slugify_dedup()
    test_paragraph_image_display_size_returns_source_extent()
    test_paragraph_image_display_size_missing_rid_returns_none()
    test_image_size_attr_emits_width_only()
    test_build_markdown_body_image_carries_source_display_size()
    test_build_markdown_body_uncaptioned_image_carries_source_display_size()
    test_paragraph_inline_markdown_wraps_bold_and_italic_runs()
    test_paragraph_inline_markdown_merges_adjacent_same_style_runs()
    test_build_markdown_body_plain_paragraph_preserves_bold()
    test_build_markdown_body_list_item_preserves_bold()
    test_extract_full_fixture()
    test_table_to_markdown_pipe()
    test_table_column_widths_in_reads_explicit_widths()
    test_table_column_widths_in_returns_none_when_unset()
    test_table_column_widths_marker_flags_unequal_widths()
    test_table_column_widths_marker_none_for_equal_widths()
    test_table_column_widths_marker_none_when_widths_unavailable()
    test_build_markdown_body_content_table_gets_column_width_marker()
    test_build_markdown_body_content_table_no_marker_for_equal_widths()
    test_extract_pdf_banner_and_text()
    test_extract_docx_cli_smoke()
    test_no_shebang_in_extractor_scripts()

    print(f"\n{passed} passed, {failed} failed (dilon-document-extractor)")
    if failed == 0:
        print("\nAll extractor tests passed!")
        return 0
    print("\nSome extractor tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
