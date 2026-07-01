"""
Test suite for Dilon Claude Tools skills.

Exercises the dilon-document-writer stub-generation logic (ported here in
Python, since the live version is plain Claude behavior described in
SKILL.md, not a script) and the dilon-document-compiler script directly,
then runs the existing output validator.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "dilon-document-compiler" / "scripts"))
import generate_dilon_doc as compiler

REPO_ROOT = Path(__file__).parent.parent
TEST_OUTPUT_DIR = Path(__file__).parent / "test-output"
WRITER_DIR = REPO_ROOT / "skills" / "dilon-document-writer"
COMPILER_DIR = REPO_ROOT / "skills" / "dilon-document-compiler"
TEMPLATE_PATH = WRITER_DIR / "TEMPLATE_Document.md"
COMPILER_SCRIPT = COMPILER_DIR / "scripts" / "generate_dilon_doc.py"
CHECK_DEPS_SCRIPT = COMPILER_DIR / "scripts" / "check_deps.py"
SIGNATURE_TEMPLATE = COMPILER_DIR / "templates" / "TEMPLATE_Word_Signature.docx"
CONTENT_TEMPLATE = COMPILER_DIR / "templates" / "TEMPLATE_Word_Content.docx"

# Scripts that must not carry a `#!/usr/bin/env python3` shebang: Windows'
# py launcher parses that line and can re-dispatch to a different,
# dependency-less python3.exe (e.g. the Microsoft Store WindowsApps stub)
# instead of the real interpreter. This project is Windows-only.
SHEBANG_GUARDED_SCRIPTS = [
    COMPILER_SCRIPT,
    CHECK_DEPS_SCRIPT,
    Path(__file__).parent / "run_tests.py",
    Path(__file__).parent / "validate-output.py",
]

SAMPLE_MARKDOWN = (
    '---\n'
    'title: "Integration Test Document"\n'
    'author: "Test Suite"\n'
    'department: "Engineering"\n'
    'doc_number: "DD_TST_99999"\n'
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
    '## 1. Purpose and Scope\n'
    '\n'
    '### 1.1 Purpose\n'
    'This document tests the compilation process.\n'
    '\n'
    '### 1.2 Scope\n'
    'Comprehensive integration testing.\n'
)

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


def generate_stub(output_path, **overrides):
    """Python port of the dilon-document-writer stub-generation logic
    (lives in SKILL.md as plain instructions for Claude; ported here so
    it can be exercised by an automated test)."""
    output_path = Path(output_path)
    if output_path.exists():
        raise FileExistsError(f"Output file already exists: {output_path}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    values = {
        "title": overrides.get("title", "Document Title"),
        "author": overrides.get("author", "Author Name"),
        "department": overrides.get("department", "--"),
        "doc_number": overrides.get("doc_number", "DD_XXX_XXXXX"),
        "current_revision": overrides.get("current_revision", "00"),
        "regulatory_rep": overrides.get("regulatory_rep", "--"),
        "quality_rep": overrides.get("quality_rep", "--"),
        "department_head": overrides.get("department_head", "--"),
        "revision_description": overrides.get("revision_description", "Initial release"),
        "eco_number": overrides.get("eco_number", "ECO-TBD"),
        "eco_date": overrides.get("eco_date", "YYYY-MM-DD"),
    }

    content = template
    content = re.sub(r'title: ".*?"', f'title: "{values["title"]}"', content, count=1)
    content = re.sub(r'author: ".*?"', f'author: "{values["author"]}"', content, count=1)
    content = re.sub(r'department: ".*?"', f'department: "{values["department"]}"', content, count=1)
    content = re.sub(r'doc_number: ".*?"', f'doc_number: "{values["doc_number"]}"', content, count=1)
    content = re.sub(r'current_revision: ".*?"', f'current_revision: "{values["current_revision"]}"', content, count=1)
    content = re.sub(r'regulatory_rep: ".*?"', f'regulatory_rep: "{values["regulatory_rep"]}"', content, count=1)
    content = re.sub(r'quality_rep: ".*?"', f'quality_rep: "{values["quality_rep"]}"', content, count=1)
    content = re.sub(r'department_head: ".*?"', f'department_head: "{values["department_head"]}"', content, count=1)
    content = re.sub(
        r'- number: ".*?"\s+description: ".*?"\s+eco_number: ".*?"\s+eco_date: ".*?"',
        '- number: "{0}"\n    description: "{1}"\n    eco_number: "{2}"\n    eco_date: "{3}"'.format(
            values["current_revision"], values["revision_description"], values["eco_number"], values["eco_date"]
        ),
        content,
        count=1,
    )

    output_path.write_text(content, encoding="utf-8")


def test_stub_custom_params():
    path = TEST_OUTPUT_DIR / "custom_stub.md"
    generate_stub(
        path,
        title="Software Requirements Specification",
        author="Engineering Team",
        doc_number="DD_SWE_12345",
        department="Software Engineering",
        current_revision="01",
    )
    check(path.exists(), "custom_stub.md created")


def test_stub_default_params():
    path = TEST_OUTPUT_DIR / "default_stub.md"
    generate_stub(path)
    check(path.exists(), "default_stub.md created")


def test_stub_duplicate_file_error():
    path = TEST_OUTPUT_DIR / "custom_stub.md"  # already created above
    raised = False
    try:
        generate_stub(path)
    except FileExistsError:
        raised = True
    check(raised, "generate_stub refuses to overwrite an existing file")


def test_ensure_blank_line_single_marker():
    result = compiler.ensure_blank_line_after_table_markers(
        '@@@TABLE_STYLE:DilonTable_Chart@@@\n| a |\n'
    )
    check(result == '@@@TABLE_STYLE:DilonTable_Chart@@@\n\n| a |\n',
          "single TABLE_STYLE marker gets a blank line inserted before the table")


def test_ensure_blank_line_stacked_style_then_columns():
    result = compiler.ensure_blank_line_after_table_markers(
        '@@@TABLE_STYLE:DilonTable_Chart@@@\n@@@TABLE_COLUMNS:1,x@@@\n| a |\n'
    )
    check(result == '@@@TABLE_STYLE:DilonTable_Chart@@@\n@@@TABLE_COLUMNS:1,x@@@\n\n| a |\n',
          "stacked STYLE+COLUMNS markers get exactly one blank line inserted after the last marker line")


def test_ensure_blank_line_stacked_columns_then_style():
    result = compiler.ensure_blank_line_after_table_markers(
        '@@@TABLE_COLUMNS:1,x@@@\n@@@TABLE_STYLE:DilonTable_Chart@@@\n| a |\n'
    )
    check(result == '@@@TABLE_COLUMNS:1,x@@@\n@@@TABLE_STYLE:DilonTable_Chart@@@\n\n| a |\n',
          "stacked COLUMNS+STYLE markers (reverse order) get exactly one blank line inserted after the last marker line")


def test_ensure_blank_line_idempotent_when_already_blank():
    already_blank = '@@@TABLE_STYLE:DilonTable_Chart@@@\n@@@TABLE_COLUMNS:1,x@@@\n\n| a |\n'
    result = compiler.ensure_blank_line_after_table_markers(already_blank)
    check(result == already_blank,
          "already-blank-line marker stack is left unchanged (no extra blank line inserted between stacked markers)")


def test_parse_column_widths_valid_with_flex():
    check(compiler.parse_column_widths('1.5,x,1,1', 4) == [1.5, 'x', 1.0, 1.0],
          "parse_column_widths accepts one 'x' entry among numeric widths")


def test_parse_column_widths_valid_all_numeric():
    check(compiler.parse_column_widths('1,2,3', 3) == [1.0, 2.0, 3.0],
          "parse_column_widths accepts an all-numeric spec with no flex column")


def test_parse_column_widths_case_insensitive_flex():
    check(compiler.parse_column_widths('1,X', 2) == [1.0, 'x'],
          "parse_column_widths treats 'X' the same as 'x'")


def test_parse_column_widths_rejects_count_mismatch():
    check(compiler.parse_column_widths('1,2', 3) is None,
          "parse_column_widths rejects a spec with fewer entries than columns")


def test_parse_column_widths_rejects_multiple_flex():
    check(compiler.parse_column_widths('x,x,1', 3) is None,
          "parse_column_widths rejects a spec with two 'x' entries")


def test_parse_column_widths_rejects_non_numeric():
    check(compiler.parse_column_widths('1,abc', 2) is None,
          "parse_column_widths rejects a non-numeric, non-'x' entry")


def test_parse_column_widths_rejects_zero_or_negative():
    check(compiler.parse_column_widths('0,1', 2) is None,
          "parse_column_widths rejects a zero-or-negative width")


def test_parse_column_widths_rejects_non_finite():
    check(compiler.parse_column_widths('1,nan', 2) is None,
          "parse_column_widths rejects a NaN width")
    check(compiler.parse_column_widths('1,inf', 2) is None,
          "parse_column_widths rejects an Infinity width")


def test_apply_table_column_widths_fixed_and_flex():
    doc = Document()
    table = doc.add_table(rows=1, cols=4)
    compiler.apply_table_column_widths(table, [1.5, 'x', 1.0, 1.0], available_width=6.27)
    widths = [round(col.width.inches, 2) for col in table.columns]
    check(widths == [1.5, 2.77, 1.0, 1.0],
          f"apply_table_column_widths sets fixed widths and computes the flex column (got {widths})")


def test_apply_table_column_widths_all_fixed():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    compiler.apply_table_column_widths(table, [2.0, 3.0], available_width=6.0)
    widths = [round(col.width.inches, 2) for col in table.columns]
    check(widths == [2.0, 3.0], f"apply_table_column_widths sets all-fixed widths as given (got {widths})")


def test_apply_table_column_widths_raises_when_flex_overflows():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    raised = False
    try:
        compiler.apply_table_column_widths(table, [5.0, 'x'], available_width=4.0)
    except ValueError:
        raised = True
    check(raised, "apply_table_column_widths raises ValueError when fixed widths leave no room for the flex column")


def test_apply_table_column_widths_raises_when_all_fixed_overflows():
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    raised = False
    try:
        compiler.apply_table_column_widths(table, [4.0, 4.0], available_width=6.0)
    except ValueError:
        raised = True
    check(raised, "apply_table_column_widths raises ValueError when all-fixed widths exceed the available width")


def test_compile_missing_input_error():
    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(TEST_OUTPUT_DIR / "nonexistent.md"),
            str(TEST_OUTPUT_DIR / "nonexistent.docx"),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode != 0, "compiler reports a non-zero exit code for a missing input file")


def test_compile_valid_document():
    input_md = TEST_OUTPUT_DIR / "compile_test.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test.docx"
    input_md.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
            str(SIGNATURE_TEMPLATE),
            str(CONTENT_TEMPLATE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 for a valid document")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    check(output_docx.exists(), "compile_test.docx created on disk")


def test_compile_bom_front_matter():
    """Regression test: a UTF-8 BOM at the start of the input markdown
    (e.g. from PowerShell's Set-Content -Encoding UTF8) must not cause the
    YAML front matter to be silently dropped."""
    input_md = TEST_OUTPUT_DIR / "compile_test_bom.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test_bom.docx"
    input_md.write_text(SAMPLE_MARKDOWN, encoding="utf-8-sig")

    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
            str(SIGNATURE_TEMPLATE),
            str(CONTENT_TEMPLATE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 for a BOM-prefixed input file")
    check("Metadata extracted: []" not in result.stdout, "BOM-prefixed front matter is not silently dropped")

    if output_docx.exists():
        doc = Document(output_docx)
        full_text = "\n".join(p.text for p in doc.paragraphs)
        # "No revision history available" is the Part B fallback text used only
        # when 'revisions' is missing from metadata - i.e. only when the YAML
        # front matter failed to parse.
        check("No revision history available" not in full_text, "revision table from BOM-prefixed file's metadata reaches the output document")
    else:
        check(False, "revision table from BOM-prefixed file's metadata reaches the output document")


TABLE_MARKER_MARKDOWN = SAMPLE_MARKDOWN + (
    '\n### 1.3 Table Test\n'
    '@@@TABLE_STYLE:DilonTable_Chart@@@\n'
    '| Thread | Zephyr Name | Priority |\n'
    '|---|---|---|\n'
    '| A | B | C |\n'
    '\n'
    '| Default | Table |\n'
    '|---|---|\n'
    '| X | Y |\n'
)


def test_compile_table_marker_no_blank_line():
    """Regression test: a @@@TABLE_STYLE@@@ marker immediately followed by
    a pipe table with no blank line (the documented convention) must
    produce a real, styled table - not garbled literal text."""
    input_md = TEST_OUTPUT_DIR / "compile_test_table_marker.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test_table_marker.docx"
    input_md.write_text(TABLE_MARKER_MARKDOWN, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
            str(SIGNATURE_TEMPLATE),
            str(CONTENT_TEMPLATE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 for a marker-adjacent table")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        check(False, "marker-adjacent table renders as a real, styled table (skipped: compile failed)")
        return

    doc = Document(output_docx)

    def header_row(table):
        return [c.text for c in table.rows[0].cells]

    marked_tables = [t for t in doc.tables if header_row(t) == ['Thread', 'Zephyr Name', 'Priority']]
    check(len(marked_tables) == 1, "marker-adjacent table survives conversion as a real table")
    if marked_tables:
        check(marked_tables[0].style is not None and marked_tables[0].style.name == 'DilonTable_Chart',
              "marker-adjacent table receives the DilonTable_Chart style")

    default_tables = [t for t in doc.tables if header_row(t) == ['Default', 'Table']]
    check(len(default_tables) == 1, "unmarked table survives conversion as a real table")
    if default_tables:
        check(default_tables[0].style is not None and default_tables[0].style.name == 'DilonTable_List',
              "unmarked table still receives the default DilonTable_List style")

    garbled = [p.text for p in doc.paragraphs if '@@@' in p.text or '|---' in p.text]
    check(not garbled, f"no leftover marker/pipe-table text in output (found: {garbled})")


COLUMN_WIDTH_MARKDOWN = SAMPLE_MARKDOWN + (
    '\n### 1.3 Column Width Test\n'
    '@@@TABLE_STYLE:DilonTable_Chart@@@\n'
    '@@@TABLE_COLUMNS:1.5,x,1,1@@@\n'
    '| Register | Address | Bit 7 | Bit 6 |\n'
    '|---|---|---|---|\n'
    '| CTRL_REG1 | 0x20 | ODR3 | ODR2 |\n'
    '\n'
    '@@@TABLE_COLUMNS:2,3@@@\n'
    '| Name | Value |\n'
    '|---|---|\n'
    '| A | B |\n'
    '\n'
    '@@@TABLE_COLUMNS:1,2@@@\n'
    '| Mismatched | Columns | Table |\n'
    '|---|---|---|\n'
    '| A | B | C |\n'
    '\n'
    '@@@TABLE_COLUMNS:10,x@@@\n'
    '| Overflow | Table |\n'
    '|---|---|\n'
    '| A | B |\n'
)


def test_compile_table_column_widths():
    """Render test: compile a document with @@@TABLE_COLUMNS@@@-marked
    tables (stacked with @@@TABLE_STYLE@@@, standalone, and two invalid
    specs) and verify the ACTUAL rendered column widths in the output
    docx match the marker's specified values - not just that
    compilation succeeded."""
    input_md = TEST_OUTPUT_DIR / "compile_test_column_widths.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test_column_widths.docx"
    input_md.write_text(COLUMN_WIDTH_MARKDOWN, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
            str(SIGNATURE_TEMPLATE),
            str(CONTENT_TEMPLATE),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 for column-width-marked tables")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        check(False, "column-width tables render with correct widths (skipped: compile failed)")
        return

    doc = Document(output_docx)

    def header_row(table):
        return [c.text for c in table.rows[0].cells]

    section = doc.sections[0]
    available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches

    # Table 1: stacked @@@TABLE_STYLE@@@ + @@@TABLE_COLUMNS:1.5,x,1,1@@@
    reg_tables = [t for t in doc.tables if header_row(t) == ['Register', 'Address', 'Bit 7', 'Bit 6']]
    check(len(reg_tables) == 1, "stacked-marker table survives conversion as a real table")
    if reg_tables:
        table = reg_tables[0]
        check(table.style is not None and table.style.name == 'DilonTable_Chart',
              "stacked-marker table still receives its DilonTable_Chart style")
        actual_widths = [round(col.width.inches, 2) for col in table.columns]
        expected_flex = round(available_width - 1.5 - 1.0 - 1.0, 2)
        expected_widths = [1.5, expected_flex, 1.0, 1.0]
        check(actual_widths == expected_widths,
              f"stacked-marker table's rendered widths match the marker spec (expected {expected_widths}, got {actual_widths})")

    # Table 2: standalone @@@TABLE_COLUMNS:2,3@@@, no @@@TABLE_STYLE@@@
    name_tables = [t for t in doc.tables if header_row(t) == ['Name', 'Value']]
    check(len(name_tables) == 1, "standalone-column-width table survives conversion as a real table")
    if name_tables:
        table = name_tables[0]
        actual_widths = [round(col.width.inches, 2) for col in table.columns]
        check(actual_widths == [2.0, 3.0],
              f"standalone all-numeric column widths render exactly as specified (got {actual_widths})")
        check(table.style is not None and table.style.name == 'DilonTable_List',
              "table with only a @@@TABLE_COLUMNS@@@ marker still gets the default DilonTable_List style")

    # Table 3: @@@TABLE_COLUMNS:1,2@@@ on a 3-column table - entry count mismatch, must warn and skip
    mismatched_tables = [t for t in doc.tables if header_row(t) == ['Mismatched', 'Columns', 'Table']]
    check(len(mismatched_tables) == 1, "entry-count-mismatch table still survives conversion as a real table")
    check("Invalid @@@TABLE_COLUMNS@@@ spec" in result.stdout,
          "entry-count-mismatch spec prints a warning instead of failing compilation")

    # Table 4: @@@TABLE_COLUMNS:10,x@@@ - fixed width alone exceeds available content width
    overflow_tables = [t for t in doc.tables if header_row(t) == ['Overflow', 'Table']]
    check(len(overflow_tables) == 1, "overflowing-width table still survives conversion as a real table")
    check("Could not apply column widths" in result.stdout,
          "overflowing column-width spec prints a warning instead of failing compilation")


def test_compile_with_default_templates():
    """Regression test for a bug where the compiler's default template
    lookup pointed at scripts/ instead of the sibling templates/ directory.
    Invokes with only <input> <output> (no template args) so the script
    must resolve its own defaults, rather than the explicit four-argument
    form SKILL.md always uses."""
    input_md = TEST_OUTPUT_DIR / "compile_test_defaults.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test_defaults.docx"
    input_md.write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(COMPILER_SCRIPT),
            str(input_md),
            str(output_docx),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 with only 2 args (default template lookup)")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    check(output_docx.exists(), "compile_test_defaults.docx created via default template lookup")


def test_no_shebang_in_python_scripts():
    def has_shebang(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        return bool(lines) and lines[0].startswith("#!")

    offenders = [str(p) for p in SHEBANG_GUARDED_SCRIPTS if has_shebang(p)]
    check(not offenders, f"no shebang lines in guarded scripts (offenders: {offenders})")


def run_validator():
    result = subprocess.run(
        [sys.executable, "validate-output.py"],
        cwd=str(Path(__file__).parent),
    )
    return result.returncode == 0


def main():
    if TEST_OUTPUT_DIR.exists():
        shutil.rmtree(TEST_OUTPUT_DIR)
    TEST_OUTPUT_DIR.mkdir(parents=True)

    test_stub_custom_params()
    test_stub_default_params()
    test_stub_duplicate_file_error()
    test_ensure_blank_line_single_marker()
    test_ensure_blank_line_stacked_style_then_columns()
    test_ensure_blank_line_stacked_columns_then_style()
    test_ensure_blank_line_idempotent_when_already_blank()
    test_parse_column_widths_valid_with_flex()
    test_parse_column_widths_valid_all_numeric()
    test_parse_column_widths_case_insensitive_flex()
    test_parse_column_widths_rejects_count_mismatch()
    test_parse_column_widths_rejects_multiple_flex()
    test_parse_column_widths_rejects_non_numeric()
    test_parse_column_widths_rejects_zero_or_negative()
    test_parse_column_widths_rejects_non_finite()
    test_apply_table_column_widths_fixed_and_flex()
    test_apply_table_column_widths_all_fixed()
    test_apply_table_column_widths_raises_when_flex_overflows()
    test_apply_table_column_widths_raises_when_all_fixed_overflows()
    test_compile_missing_input_error()
    test_compile_valid_document()
    test_compile_bom_front_matter()
    test_compile_table_marker_no_blank_line()
    test_compile_table_column_widths()
    test_compile_with_default_templates()
    test_no_shebang_in_python_scripts()

    print(f"\n{passed} passed, {failed} failed (direct-invocation checks)")

    validator_ok = run_validator()

    if failed == 0 and validator_ok:
        print("\nAll tests passed!")
        return 0
    print("\nSome tests failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
