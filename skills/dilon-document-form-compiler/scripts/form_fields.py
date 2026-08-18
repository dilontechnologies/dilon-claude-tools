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
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches
from docx.text.paragraph import Paragraph

FORM_FIELD_RE = re.compile(r'@@@FORM_FIELD:(\w+)@@@(.*?)@@@END_FORM_FIELD@@@', re.DOTALL)

BRACKET_ANNOTATION_RE = re.compile(r'^(.*?)\[([^\[\]]+)\]\s*$')


def _parse_key_value_pairs(annotation_text):
    """Split a comma-separated `key=value,key=value` string into a dict.
    Entries without '=' are ignored, not an error."""
    annotations = {}
    for entry in annotation_text.split(','):
        if '=' not in entry:
            continue
        key, value = entry.split('=', 1)
        annotations[key.strip()] = value.strip()
    return annotations


def parse_bracket_annotations(text):
    """
    Split a trailing `[key=value,key=value,...]` annotation off `text`.

    Returns (cleaned_text, annotations) where annotations is a
    str -> str dict (values are not type-converted here - callers parse
    ints/floats themselves). Returns (text, {}) if there's no trailing
    bracket.
    """
    match = BRACKET_ANNOTATION_RE.match(text)
    if not match:
        return text, {}
    return match.group(1), _parse_key_value_pairs(match.group(2))


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


def underscore_until_end_of_line(paragraph, width_override=None, num_lines=1):
    """
    Rewrite `paragraph` (currently just its label text, e.g. "Work
    Order:") into one or more right-aligned, underscore-leadered blank
    lines.

    width_override: explicit blank length in inches for the (single)
        label line. Ignored - with a warning - if num_lines > 1, since
        multi-line blanks always span the full available width. Clamped
        - with a warning - if it exceeds the available width in context.
    num_lines: total number of blank lines. 1 (default) keeps the
        original single "<label>\\t" paragraph. >1 appends num_lines - 1
        additional full-width blank paragraphs immediately after the
        label paragraph, each with its own tab stop.

    Word computes the resulting fill-to-the-edge blank(s) at render time;
    nothing here counts characters.
    """
    label = paragraph.text
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)

    available_width = _paragraph_available_width_inches(paragraph)

    if num_lines > 1:
        if width_override is not None:
            print(f"  FillLine: width= ignored because lines={num_lines} (multi-line blanks always span the full available width)")
        line_width = available_width
    elif width_override is not None:
        if width_override > available_width:
            print(f"  FillLine: width={width_override}in exceeds the available width ({available_width}in) - clamped")
            line_width = available_width
        else:
            line_width = width_override
    else:
        line_width = available_width

    paragraph.paragraph_format.tab_stops.add_tab_stop(
        Inches(line_width), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.LINES
    )
    paragraph.add_run(f"{label}\t")

    previous_p = paragraph._p
    for _ in range(num_lines - 1):
        new_p = OxmlElement('w:p')
        previous_p.addnext(new_p)
        previous_p = new_p
        new_paragraph = Paragraph(new_p, paragraph._parent)
        new_paragraph.paragraph_format.tab_stops.add_tab_stop(
            Inches(line_width), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.LINES
        )
        new_paragraph.add_run("\t")


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
            cleaned_label, annotations = parse_bracket_annotations(label)

            width_override = None
            if 'width' in annotations:
                width_match = re.match(r'^([\d.]+)in$', annotations['width'])
                if width_match:
                    width_override = float(width_match.group(1))
                else:
                    print(f"  FillLine: invalid width={annotations['width']!r} - ignoring")

            num_lines = 1
            if 'lines' in annotations:
                try:
                    num_lines = int(annotations['lines'])
                    if num_lines < 1:
                        print(f"  FillLine: lines={annotations['lines']!r} must be >= 1 - using 1")
                        num_lines = 1
                except ValueError:
                    print(f"  FillLine: invalid lines={annotations['lines']!r} - ignoring")

            for run in list(para.runs):
                run._element.getparent().remove(run._element)
            para.add_run(cleaned_label)
            underscore_until_end_of_line(para, width_override=width_override, num_lines=num_lines)
            changed = True
        else:
            print(f"  Unrecognized @@@FORM_FIELD:{function_name}@@@ - leaving marker text as-is")

    if changed:
        doc.save(docx_file)
