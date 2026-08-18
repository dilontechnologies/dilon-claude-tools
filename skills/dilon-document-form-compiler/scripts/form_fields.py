"""
Form-specific markdown-authoring functions for dilon-document-form-compiler.

These live outside lib/dilon_docx_common.py deliberately: ordinary content
documents (dilon-document-compiler) never need them. Uses its own
@@@FORM_FIELD:Name@@@...@@@END_FORM_FIELD@@@ marker family so it never
collides with the shared module's @@@STYLE@@@/@@@TABLE_STYLE@@@ markers.
"""

import re

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn
from docx.shared import Inches

FORM_FIELD_RE = re.compile(r'@@@FORM_FIELD:(\w+)@@@(.*?)@@@END_FORM_FIELD@@@', re.DOTALL)


def _enclosing_table_cell(paragraph):
    """Return the nearest enclosing <w:tc> XML element, or None if
    `paragraph` is body-level (not inside a table cell)."""
    tc = paragraph._p.getparent()
    while tc is not None and tc.tag != qn('w:tc'):
        tc = tc.getparent()
    return tc


def _paragraph_available_width_inches(paragraph):
    """Return the available width (inches) for a fill-to-end-of-line tab
    stop: the enclosing table cell's width if the paragraph lives in a
    table cell, otherwise the page's content width (page width minus
    margins)."""
    tc = _enclosing_table_cell(paragraph)

    if tc is not None:
        tc_pr = tc.find(qn('w:tcPr'))
        if tc_pr is not None:
            tc_w = tc_pr.find(qn('w:tcW'))
            if tc_w is not None and tc_w.get(qn('w:w')):
                # tcW is in twentieths of a point (dxa); 1440 dxa = 1 inch
                return int(tc_w.get(qn('w:w'))) / 1440.0

    doc = paragraph.part.document
    section = doc.sections[0]
    return section.page_width.inches - section.left_margin.inches - section.right_margin.inches


def _iter_table_paragraphs(table):
    """Yield every paragraph inside `table`'s cells, recursing into any
    nested tables (a cell can itself contain a table)."""
    for row in table.rows:
        for cell in row.cells:
            yield from cell.paragraphs
            for nested_table in cell.tables:
                yield from _iter_table_paragraphs(nested_table)


def _iter_all_paragraphs(doc):
    """Yield every paragraph in `doc` - body-level paragraphs plus every
    paragraph inside every table cell (recursively). python-docx's
    `doc.paragraphs` alone only sees body-level paragraphs, silently
    skipping markers placed inside markdown table cells."""
    yield from doc.paragraphs
    for table in doc.tables:
        yield from _iter_table_paragraphs(table)


def underscore_until_end_of_line(paragraph):
    """
    Rewrite `paragraph` (currently just its label text, e.g. "Work
    Order:") into "<label>\\t" with a right-aligned, underscore-leadered
    tab stop positioned at the true available width - the enclosing table
    cell's width if the paragraph is in a table cell, otherwise the page's
    content width. Word computes the resulting fill-to-the-edge blank at
    render time; nothing here counts characters.
    """
    label = paragraph.text
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)

    width = _paragraph_available_width_inches(paragraph)
    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(width), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.LINES
    )
    paragraph.add_run(f"{label}\t")


def apply_form_fields(docx_file):
    """
    Scan docx_file for @@@FORM_FIELD:Name@@@...@@@END_FORM_FIELD@@@
    markers and apply the matching form-specific function. Currently
    supports 'FillLine' (underscore_until_end_of_line). Unrecognized
    function names are left as plain text with a printed warning, matching
    the shared module's warn-and-degrade convention - never a hard
    failure.
    """
    doc = Document(docx_file)
    changed = False

    for para in list(_iter_all_paragraphs(doc)):
        match = FORM_FIELD_RE.search(para.text)
        if not match:
            continue

        function_name, label = match.group(1), match.group(2)
        if function_name == "FillLine":
            for run in list(para.runs):
                run._element.getparent().remove(run._element)
            para.add_run(label)
            underscore_until_end_of_line(para)
            changed = True
        else:
            print(f"  Unrecognized @@@FORM_FIELD:{function_name}@@@ - leaving marker text as-is")

    if changed:
        doc.save(docx_file)
