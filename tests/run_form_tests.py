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


def test_parse_bracket_annotations():
    import form_fields as ff
    check(ff.parse_bracket_annotations("Work Order:") == ("Work Order:", {}), "no bracket -> unchanged text, empty annotations")
    check(ff.parse_bracket_annotations("Cure Temp:[pair=60]") == ("Cure Temp:", {"pair": "60"}), "single annotation parsed")
    check(
        ff.parse_bracket_annotations("Notes:[dir=v,rows=3]") == ("Notes:", {"dir": "v", "rows": "3"}),
        "multiple comma-separated annotations parsed",
    )
    check(ff.parse_bracket_annotations("Label[malformed]") == ("Label", {}), "entry without '=' is ignored, not an error")


def test_underscore_until_end_of_line_width_override():
    import form_fields as ff
    doc = Document()
    p = doc.add_paragraph("Work Order:")
    ff.underscore_until_end_of_line(p, width_override=3.0)

    tab_stops = p.paragraph_format.tab_stops
    check(len(tab_stops) == 1, f"exactly one tab stop added, found {len(tab_stops)}")
    if len(tab_stops) == 1:
        check(abs(tab_stops[0].position.inches - 3.0) < 0.01, f"tab stop positioned at the given width (3.0in), got {tab_stops[0].position.inches}in")


def test_underscore_until_end_of_line_width_override_clamped():
    import form_fields as ff
    doc = Document()
    p = doc.add_paragraph("Work Order:")
    section = doc.sections[0]
    available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches
    ff.underscore_until_end_of_line(p, width_override=available_width + 5.0)

    tab_stops = p.paragraph_format.tab_stops
    check(
        len(tab_stops) == 1 and abs(tab_stops[0].position.inches - available_width) < 0.01,
        f"width_override exceeding the available width is clamped to it ({available_width}in), got "
        f"{tab_stops[0].position.inches if len(tab_stops) == 1 else 'N/A'}in",
    )


def test_underscore_until_end_of_line_multiple_lines():
    import form_fields as ff
    doc = Document()
    p = doc.add_paragraph("Notes:")
    ff.underscore_until_end_of_line(p, num_lines=3)

    all_paragraphs = doc.paragraphs
    check(len(all_paragraphs) == 3, f"num_lines=3 produces 3 paragraphs, found {len(all_paragraphs)}")
    if len(all_paragraphs) == 3:
        check(all_paragraphs[0].text == "Notes:\t", f"first paragraph keeps the label, got {all_paragraphs[0].text!r}")
        check(all_paragraphs[1].text == "\t", f"extra line is a bare tab, got {all_paragraphs[1].text!r}")
        check(all_paragraphs[2].text == "\t", f"extra line is a bare tab, got {all_paragraphs[2].text!r}")
        for para in all_paragraphs:
            tab_stops = para.paragraph_format.tab_stops
            check(len(tab_stops) == 1, f"each line has exactly one tab stop, found {len(tab_stops)}")


def test_underscore_until_end_of_line_multiple_lines_ignores_width():
    import form_fields as ff
    doc = Document()
    p = doc.add_paragraph("Notes:")
    section = doc.sections[0]
    available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches
    ff.underscore_until_end_of_line(p, width_override=2.0, num_lines=2)

    for para in doc.paragraphs:
        tab_stops = para.paragraph_format.tab_stops
        check(
            len(tab_stops) == 1 and abs(tab_stops[0].position.inches - available_width) < 0.01,
            f"num_lines > 1 ignores width_override, expected {available_width}in, got "
            f"{tab_stops[0].position.inches if len(tab_stops) == 1 else 'N/A'}in",
        )


def test_apply_form_fields_fillline_width_annotation():
    import form_fields as ff
    doc = Document()
    doc.add_paragraph("@@@FORM_FIELD:FillLine@@@Work Order:[width=3in]@@@END_FORM_FIELD@@@")
    temp_path = TEST_OUTPUT_DIR / "form_fields_fillline_width.docx"
    doc.save(temp_path)

    ff.apply_form_fields(temp_path)

    result_doc = Document(temp_path)
    check(result_doc.paragraphs[0].text == "Work Order:\t", f"annotation stripped from label, got {result_doc.paragraphs[0].text!r}")
    tab_stops = result_doc.paragraphs[0].paragraph_format.tab_stops
    check(
        len(tab_stops) == 1 and abs(tab_stops[0].position.inches - 3.0) < 0.01,
        f"width=3in annotation applied, got {tab_stops[0].position.inches if len(tab_stops) == 1 else 'N/A'}in",
    )


def test_apply_form_fields_fillline_lines_annotation():
    import form_fields as ff
    doc = Document()
    doc.add_paragraph("@@@FORM_FIELD:FillLine@@@Notes:[lines=3]@@@END_FORM_FIELD@@@")
    temp_path = TEST_OUTPUT_DIR / "form_fields_fillline_lines.docx"
    doc.save(temp_path)

    ff.apply_form_fields(temp_path)

    result_doc = Document(temp_path)
    check(len(result_doc.paragraphs) == 3, f"lines=3 annotation produces 3 paragraphs, found {len(result_doc.paragraphs)}")
    check(result_doc.paragraphs[0].text == "Notes:\t", f"first paragraph keeps the label, got {result_doc.paragraphs[0].text!r}")


def test_form_field_re_optional_width_group():
    import form_fields as ff
    match = ff.FORM_FIELD_RE.search("@@@FORM_FIELD:FieldGrid:6.5in@@@Work Order:@@@END_FORM_FIELD@@@")
    check(match is not None, "marker with a block-level width suffix matches")
    if match:
        check(match.group(1) == "FieldGrid", f"function name captured, got {match.group(1)!r}")
        check(match.group(2) == "6.5in", f"width suffix captured, got {match.group(2)!r}")
        check(match.group(3) == "Work Order:", f"block content captured, got {match.group(3)!r}")

    match_no_width = ff.FORM_FIELD_RE.search("@@@FORM_FIELD:FillLine@@@Work Order:@@@END_FORM_FIELD@@@")
    check(match_no_width is not None, "marker without a width suffix still matches")
    if match_no_width:
        check(match_no_width.group(2) is None, "width group is None when no suffix is given")
        check(match_no_width.group(3) == "Work Order:", f"block content captured, got {match_no_width.group(3)!r}")


def test_parse_row_annotation():
    import form_fields as ff
    check(ff.parse_row_annotation("Work Order: | Date:") == ("Work Order: | Date:", {}), "no row annotation -> unchanged, empty dict")
    check(ff.parse_row_annotation("Notes: {dir=v,rows=3}") == ("Notes:", {"dir": "v", "rows": "3"}), "row annotation parsed and stripped")


def test_parse_field_grid_block_simple():
    import form_fields as ff
    block = "Work Order: | Date:\nCarrier Board Assy Lot:\n"
    rows = ff.parse_field_grid_block(block)
    check(len(rows) == 2, f"two declared rows produce two parsed rows, found {len(rows)}")
    if len(rows) == 2:
        check(rows[0]['pairs'] == [("Work Order:", {}), ("Date:", {})], f"first row's pairs, got {rows[0]['pairs']!r}")
        check(rows[0]['annotations'] == {}, "first row has no row-level annotations")
        check(rows[1]['pairs'] == [("Carrier Board Assy Lot:", {})], f"second row's single pair, got {rows[1]['pairs']!r}")


def test_parse_field_grid_block_annotations():
    import form_fields as ff
    block = "Cure Temp:[pair=60] | Start Time:[pair=40]\nNotes: {dir=v,rows=3}\n"
    rows = ff.parse_field_grid_block(block)
    check(len(rows) == 2, f"expected 2 rows, found {len(rows)}")
    if len(rows) == 2:
        check(
            rows[0]['pairs'] == [("Cure Temp:", {"pair": "60"}), ("Start Time:", {"pair": "40"})],
            f"per-pair annotations parsed, got {rows[0]['pairs']!r}",
        )
        check(rows[1]['pairs'] == [("Notes:", {})], f"row-level annotation not mistaken for a per-pair one, got {rows[1]['pairs']!r}")
        check(rows[1]['annotations'] == {"dir": "v", "rows": "3"}, f"row-level annotations parsed, got {rows[1]['annotations']!r}")


def test_parse_field_grid_block_skips_blank_and_unparseable_lines():
    import form_fields as ff
    block = "Work Order:\n\n   \n|\nDate:\n"
    rows = ff.parse_field_grid_block(block)
    check(len(rows) == 2, f"blank lines and an unparseable row are skipped, found {len(rows)} rows")
    if len(rows) == 2:
        check(rows[0]['pairs'] == [("Work Order:", {})], f"got {rows[0]['pairs']!r}")
        check(rows[1]['pairs'] == [("Date:", {})], f"got {rows[1]['pairs']!r}")


def test_resolve_row_settings_defaults_and_overrides():
    import form_fields as ff
    check(ff.resolve_row_settings({}) == ('h', 1), "defaults to horizontal, rows=1")
    check(ff.resolve_row_settings({'dir': 'v', 'rows': '3'}) == ('v', 3), "explicit dir/rows honored")
    check(ff.resolve_row_settings({'dir': 'sideways'}) == ('h', 1), "invalid dir falls back to 'h'")
    check(ff.resolve_row_settings({'rows': '0'}) == ('h', 1), "rows < 1 falls back to 1")
    check(ff.resolve_row_settings({'rows': 'abc'}) == ('h', 1), "non-numeric rows falls back to 1")


def test_resolve_pair_rows():
    import form_fields as ff
    check(ff.resolve_pair_rows({}, 2) == 2, "falls back to the row default when absent")
    check(ff.resolve_pair_rows({'rows': '5'}, 2) == 5, "per-pair override takes precedence")
    check(ff.resolve_pair_rows({'rows': '0'}, 2) == 2, "invalid override falls back to the row default")


def test_resolve_pair_widths_even_split():
    import form_fields as ff
    pairs = [("A:", {}), ("B:", {})]
    widths = ff.resolve_pair_widths(pairs, 6.0)
    check(widths == [3.0, 3.0], f"default even split across 2 pairs, got {widths}")

    pairs3 = [("A:", {}), ("B:", {}), ("C:", {})]
    widths3 = ff.resolve_pair_widths(pairs3, 6.0)
    check(widths3 == [2.0, 2.0, 2.0], f"default even split across 3 pairs, got {widths3}")


def test_resolve_pair_widths_explicit_and_remainder():
    import form_fields as ff
    pairs = [("A:", {'pair': '60'}), ("B:", {})]
    widths = ff.resolve_pair_widths(pairs, 10.0)
    check(widths == [6.0, 4.0], f"explicit pair=60 with remainder auto-filled, got {widths}")


def test_resolve_pair_widths_overshoot_falls_back():
    import form_fields as ff
    pairs = [("A:", {'pair': '60'}), ("B:", {'pair': '50'})]
    widths = ff.resolve_pair_widths(pairs, 10.0)
    check(widths == [5.0, 5.0], f"declared total > 100 falls back to an even split, got {widths}")


def test_resolve_pair_widths_nonpositive_remainder_falls_back():
    import form_fields as ff
    pairs = [("A:", {'pair': '100'}), ("B:", {})]
    widths = ff.resolve_pair_widths(pairs, 10.0)
    check(widths == [5.0, 5.0], f"a fully-declared pair leaving no room for an undeclared one falls back to an even split, got {widths}")


def test_resolve_label_width():
    import form_fields as ff
    check(ff.resolve_label_width({}, 10.0, 'h') == (5.0, 5.0), "default 50/50 split")
    check(ff.resolve_label_width({'label': '70'}, 10.0, 'h') == (7.0, 3.0), "explicit label= split")
    check(ff.resolve_label_width({'label': '70'}, 10.0, 'v') == (None, None), "dir=v ignores label=, returns (None, None)")
    check(ff.resolve_label_width({}, 10.0, 'v') == (None, None), "dir=v with no label= still returns (None, None)")


def test_build_field_grid_row_table_horizontal():
    import form_fields as ff
    doc = Document()
    row = {'pairs': [("Work Order:", {}), ("Date:", {})], 'annotations': {}}
    table = ff.build_field_grid_row_table(doc, row, 6.0)

    check(table.style.name == "Table Grid", f"row-table uses the Table Grid style, got {table.style.name!r}")
    check(len(table.columns) == 4, f"2 horizontal pairs produce 4 columns, found {len(table.columns)}")
    cells = table.rows[0].cells
    check(cells[0].paragraphs[0].text == "Work Order:", f"first label cell text, got {cells[0].paragraphs[0].text!r}")
    check(cells[1].text == "", "first blank cell starts empty")
    check(cells[2].paragraphs[0].text == "Date:", f"second label cell text, got {cells[2].paragraphs[0].text!r}")
    check(cells[3].text == "", "second blank cell starts empty")
    check(len(cells[1].paragraphs) == 1, f"rows=1 default: blank cell has exactly 1 paragraph, found {len(cells[1].paragraphs)}")


def test_build_field_grid_row_table_vertical_with_rows():
    import form_fields as ff
    doc = Document()
    row = {'pairs': [("Notes:", {})], 'annotations': {'dir': 'v', 'rows': '3'}}
    table = ff.build_field_grid_row_table(doc, row, 6.0)

    check(len(table.columns) == 1, f"1 vertical pair produces 1 column, found {len(table.columns)}")
    cell = table.rows[0].cells[0]
    check(cell.paragraphs[0].text == "Notes:", f"label paragraph text, got {cell.paragraphs[0].text!r}")
    check(len(cell.paragraphs) == 4, f"1 label paragraph + rows=3 blank paragraphs = 4 total, found {len(cell.paragraphs)}")
    for blank_paragraph in cell.paragraphs[1:]:
        check(blank_paragraph.text == "", f"blank paragraph is empty, got {blank_paragraph.text!r}")


def test_build_field_grid_row_table_is_centered():
    import form_fields as ff
    from docx.enum.table import WD_TABLE_ALIGNMENT
    doc = Document()
    row = {'pairs': [("A:", {})], 'annotations': {}}
    table = ff.build_field_grid_row_table(doc, row, 6.0)
    check(table.alignment == WD_TABLE_ALIGNMENT.CENTER, f"row-table is centered, got {table.alignment}")


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
    test_parse_bracket_annotations()
    test_underscore_until_end_of_line_width_override()
    test_underscore_until_end_of_line_width_override_clamped()
    test_underscore_until_end_of_line_multiple_lines()
    test_underscore_until_end_of_line_multiple_lines_ignores_width()
    test_apply_form_fields_fillline_width_annotation()
    test_apply_form_fields_fillline_lines_annotation()
    test_form_field_re_optional_width_group()
    test_parse_row_annotation()
    test_parse_field_grid_block_simple()
    test_parse_field_grid_block_annotations()
    test_parse_field_grid_block_skips_blank_and_unparseable_lines()
    test_resolve_row_settings_defaults_and_overrides()
    test_resolve_pair_rows()
    test_resolve_pair_widths_even_split()
    test_resolve_pair_widths_explicit_and_remainder()
    test_resolve_pair_widths_overshoot_falls_back()
    test_resolve_pair_widths_nonpositive_remainder_falls_back()
    test_resolve_label_width()
    test_build_field_grid_row_table_horizontal()
    test_build_field_grid_row_table_vertical_with_rows()
    test_build_field_grid_row_table_is_centered()
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
