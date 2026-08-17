# -*- coding: utf-8 -*-
"""
Shared Pandoc-conversion and Word-styling helpers used by both
dilon-document-compiler and dilon-document-form-compiler.

Moved out of generate_dilon_doc.py as a pure refactor - see
docs/superpowers/specs/2026-08-17-document-extraction-and-form-tooling-design.md
(dilon-claude-tools repo) for why these two skills share this module.
"""

import math
import re
import subprocess
from pathlib import Path

from docx import Document
from docx.shared import Inches
from docxcompose.composer import Composer


def apply_table_style_to_object(table, style_name):
    """
    Apply a custom table style to a single table object.

    Args:
        table: python-docx Table object
        style_name: Name of the table style to apply
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    # Apply the table style
    table.style = style_name

    # Get or create tblPr element
    tbl_pr = table._element.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement('w:tblPr')
        table._element.insert(0, tbl_pr)

    # Get or create tblLook element
    tbl_look = tbl_pr.find(qn('w:tblLook'))
    if tbl_look is None:
        tbl_look = OxmlElement('w:tblLook')
        tbl_pr.append(tbl_look)

    # Set table style options based on the style name
    if style_name == 'DilonTable_Chart':
        # Enable both header row and first column
        tbl_look.set(qn('w:val'), '04A0')
        tbl_look.set(qn('w:firstRow'), '1')
        tbl_look.set(qn('w:firstColumn'), '1')
        tbl_look.set(qn('w:lastRow'), '0')
        tbl_look.set(qn('w:lastColumn'), '0')
        tbl_look.set(qn('w:noHBand'), '0')
        tbl_look.set(qn('w:noVBand'), '1')
    elif style_name == 'DilonTable_List':
        # Enable header row only
        tbl_look.set(qn('w:val'), '0400')
        tbl_look.set(qn('w:firstRow'), '1')
        tbl_look.set(qn('w:firstColumn'), '0')
        tbl_look.set(qn('w:lastRow'), '0')
        tbl_look.set(qn('w:lastColumn'), '0')
        tbl_look.set(qn('w:noHBand'), '0')
        tbl_look.set(qn('w:noVBand'), '1')


def apply_paragraph_style_to_objects(paragraphs, style_name):
    """
    Apply a custom paragraph style to a list of paragraph objects.

    Args:
        paragraphs: List of python-docx Paragraph objects
        style_name: Name of the paragraph style to apply
    """
    for para in paragraphs:
        para.style = style_name


def parse_column_widths(spec_text, num_columns):
    """
    Parse a @@@TABLE_COLUMNS:...@@@ marker's contents into a per-column
    width spec.

    Returns a list of length num_columns where each entry is a positive
    float (inches) or the string 'x' (flex column), or None if the spec
    is invalid: wrong entry count, 2+ 'x' entries, or an entry
    that isn't a positive number or 'x'/'X'.
    """
    entries = [entry.strip() for entry in spec_text.split(',')]
    if len(entries) != num_columns:
        return None

    parsed = []
    flex_count = 0
    for entry in entries:
        if entry.lower() == 'x':
            flex_count += 1
            parsed.append('x')
            continue

        try:
            value = float(entry)
        except ValueError:
            return None
        if value <= 0 or not math.isfinite(value):
            return None
        parsed.append(value)

    if flex_count > 1:
        return None

    return parsed


def apply_table_column_widths(table, widths, available_width):
    """
    Set explicit per-column widths (inches) on a table.

    widths: list as returned by parse_column_widths() - one entry per
    column, each a positive float (inches) or 'x' (flex column).
    available_width: total content width in inches (page width minus
    margins) the table's columns must not exceed.

    Raises ValueError if the fixed widths leave no room for a flex
    column, or if there's no flex column and the fixed widths alone
    exceed available_width.
    """
    fixed_total = sum(width for width in widths if width != 'x')
    has_flex = 'x' in widths

    if has_flex:
        flex_width = available_width - fixed_total
        if flex_width <= 0:
            raise ValueError(
                f"fixed column widths ({fixed_total}in) leave no room for the "
                f"flex column within the available width ({available_width}in)"
            )
    elif fixed_total > available_width:
        raise ValueError(
            f"column widths ({fixed_total}in) exceed the available width ({available_width}in)"
        )

    table.autofit = False
    for idx, width in enumerate(widths):
        value = flex_width if width == 'x' else width
        emu_width = Inches(value)
        table.columns[idx].width = emu_width
        for cell in table.columns[idx].cells:
            cell.width = emu_width


def apply_styles(docx_file):
    """
    Apply custom styles to tables and paragraphs based on @@@ markers in the Word document.

    Uses a state machine to scan the document once:
    - NO_MARKER: Default state, looking for @@@ markers
    - PARAGRAPH_MARKER: Found paragraph start marker, searching for END_STYLE

    States:
        NO_MARKER -> NO_MARKER (found @@@TABLE_STYLE:...@@@ - handled immediately)
        NO_MARKER -> PARAGRAPH_MARKER (found @@@STYLE:...@@@ without END on same line)
        NO_MARKER -> NO_MARKER (found @@@STYLE:...@@@ with END on same line)
        PARAGRAPH_MARKER -> NO_MARKER (found @@@END_STYLE@@@)

    Args:
        docx_file: Path to the Word document
    """
    doc = Document(docx_file)

    # State machine states
    NO_MARKER = 0
    PARAGRAPH_MARKER = 1

    state = NO_MARKER

    # State variables
    saved_style_name = None
    paragraph_start = None

    # Operation collections
    table_operations = []  # List of (table_object, style_name)
    styled_table_elements = set()  # Set of XML elements for tables that received explicit styles
    column_width_operations = []  # List of (table_object, columns_spec_text)
    paragraph_operations = []  # List of (start_idx, end_idx, style_name)
    paragraphs_to_trim = []  # List of (idx, cleaned_text)

    print(f"  Scanning document with state machine...")

    # PHASE 1: Single-pass scan with state machine
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()

        if state == NO_MARKER:
            # Early exit: skip paragraphs without markers
            if '@@@' not in text:
                continue

            # Skip code blocks to avoid processing documentation examples
            if para.runs and para.runs[0].style and 'Verbatim' in para.runs[0].style.name:
                continue

            # Handle table style / column-width markers (must start the
            # paragraph; either marker may lead when both are stacked,
            # since Pandoc merges adjacent no-blank-line marker lines into
            # a single paragraph)
            if text.startswith('@@@TABLE_STYLE:') or text.startswith('@@@TABLE_COLUMNS:'):
                style_match = re.search(r'@@@TABLE_STYLE:(\w+)@@@', text)
                columns_match = re.search(r'@@@TABLE_COLUMNS:([\w.,\s]+)@@@', text)

                if style_match or columns_match:
                    next_element = para._element.getnext()

                    # Check if immediate next element is a table
                    table_obj = None
                    if next_element is not None and next_element.tag.endswith('tbl'):
                        # Find the Table object that wraps this XML element
                        for table in doc.tables:
                            if table._element == next_element:
                                table_obj = table
                                break

                    if table_obj is not None:
                        if style_match:
                            style_name = style_match.group(1)
                            table_operations.append((table_obj, style_name))
                            styled_table_elements.add(table_obj._element)
                        if columns_match:
                            column_width_operations.append((table_obj, columns_match.group(1)))
                    else:
                        print(f"  Table marker '{text[:60]}' at paragraph {i} not followed by table")

                    # Mark marker paragraph for deletion
                    paragraphs_to_trim.append((i, ''))

            # Handle paragraph style markers (must start the paragraph)
            elif text.startswith('@@@STYLE:'):
                style_match = re.search(r'@@@STYLE:(\w+)@@@', text)
                if style_match:
                    saved_style_name = style_match.group(1)

                    # Check for inline case (both markers in same paragraph)
                    if text.endswith('@@@END_STYLE@@@'):
                        cleaned_text = re.sub(r'@@@STYLE:\w+@@@|@@@END_STYLE@@@', '', text).strip()
                        paragraph_operations.append((i, i, saved_style_name))
                        paragraphs_to_trim.append((i, cleaned_text))
                    else:
                        # Multi-paragraph case: save start position and transition
                        paragraph_start = i
                        state = PARAGRAPH_MARKER

        elif state == PARAGRAPH_MARKER:
            # Skip code blocks while searching for END marker
            if para.runs and para.runs[0].style and 'Verbatim' in para.runs[0].style.name:
                continue

            # Look for END marker
            if text.endswith('@@@END_STYLE@@@'):
                paragraph_operations.append((paragraph_start, i, saved_style_name))

                # Mark all paragraphs in range for trimming
                for k in range(paragraph_start, i + 1):
                    para_to_trim = doc.paragraphs[k]

                    if para_to_trim.runs and para_to_trim.runs[0].style and 'Verbatim' in para_to_trim.runs[0].style.name:
                        continue

                    original_text = para_to_trim.text
                    cleaned_text = re.sub(r'@@@STYLE:\w+@@@|@@@END_STYLE@@@', '', original_text).strip()

                    if original_text.strip() != cleaned_text:
                        paragraphs_to_trim.append((k, cleaned_text))

                # Transition back to NO_MARKER
                state = NO_MARKER
                saved_style_name = None
                paragraph_start = None

    # Check for unclosed blocks
    if state == PARAGRAPH_MARKER:
        print(f"  Found START marker at paragraph {paragraph_start} but no valid END marker")

    # Add default styles to unstyled tables
    for table in doc.tables:
        if table._element not in styled_table_elements:
            table_operations.append((table, 'DilonTable_List'))

    # PHASE 2: Execute all collected operations
    # Apply table styles
    for table, style_name in table_operations:
        try:
            apply_table_style_to_object(table, style_name)
        except Exception as e:
            print(f"  Could not apply style '{style_name}' to table: {e}")

    # Apply column widths
    if column_width_operations:
        section = doc.sections[0]
        available_width = section.page_width.inches - section.left_margin.inches - section.right_margin.inches

        for table, spec_text in column_width_operations:
            widths = parse_column_widths(spec_text, len(table.columns))
            if widths is None:
                print(f"  Invalid @@@TABLE_COLUMNS@@@ spec '{spec_text}' for a {len(table.columns)}-column table; leaving default widths")
                continue
            try:
                apply_table_column_widths(table, widths, available_width)
            except ValueError as e:
                print(f"  Could not apply column widths '{spec_text}': {e}")

    # Apply paragraph styles
    for start_idx, end_idx, style_name in paragraph_operations:
        try:
            paras = [doc.paragraphs[k] for k in range(start_idx, end_idx + 1)]
            apply_paragraph_style_to_objects(paras, style_name)
        except Exception as e:
            print(f"  Could not apply style '{style_name}' to paragraphs {start_idx}-{end_idx}: {e}")

    # Clean up marker paragraphs (reverse order to maintain indices)
    paragraphs_to_delete = []
    for idx, cleaned_text in sorted(paragraphs_to_trim, reverse=True):
        para = doc.paragraphs[idx]

        if cleaned_text:
            # Trim markers but keep content
            for run in para.runs:
                run._element.getparent().remove(run._element)
            para.add_run(cleaned_text)
        else:
            p_element = para._element
            prev_element = p_element.getprevious()
            next_element = p_element.getnext()
            between_two_tables = (
                prev_element is not None and prev_element.tag.endswith('tbl')
                and next_element is not None and next_element.tag.endswith('tbl')
            )

            if between_two_tables:
                # Deleting this paragraph would leave the two tables
                # directly adjacent in the XML, which Word merges into a
                # single visual table on open. Empty it instead so a
                # blank paragraph keeps separating them.
                for run in para.runs:
                    run._element.getparent().remove(run._element)
            else:
                # Delete paragraph entirely (marker only)
                paragraphs_to_delete.append(idx)
                p_element.getparent().remove(p_element)

    if paragraphs_to_delete:
        print(f"  Removed {len(paragraphs_to_delete)} marker paragraph(s)")

    doc.save(docx_file)


def _add_field_simple_run(paragraph, instr, cached_text):
    """
    Append a Word fldSimple field (e.g. STYLEREF/SEQ) to a paragraph, with
    cached_text as the field's placeholder display value until Word
    recalculates it (Word shows this cached result until the field is
    updated - see set_update_fields_on_open()).
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    fld = OxmlElement('w:fldSimple')
    fld.set(qn('w:instr'), instr)
    run_el = OxmlElement('w:r')
    r_pr = OxmlElement('w:rPr')
    r_pr.append(OxmlElement('w:noProof'))
    run_el.append(r_pr)
    t_el = OxmlElement('w:t')
    t_el.text = cached_text
    run_el.append(t_el)
    fld.append(run_el)
    paragraph._p.append(fld)


def apply_figure_captions(docx_file):
    """
    Turn Pandoc's implicit-figure caption paragraphs into Word-native,
    auto-numbered figure captions.

    MARKDOWN_STYLING_GUIDE.md documents the authoring convention:
    `![Description.](path.png){#fig:label}` - the caption text lives in
    the image's alt-text brackets, with no manually-typed figure number.
    Because the "Captioned Figure" / "Image Caption" paragraph styles are
    defined in the reference template (see TEMPLATE_Word_Signature.docx),
    Pandoc routes an image-with-alt-text into a distinct "Image Caption"
    paragraph - a reliable, unambiguous signal that this is a real figure
    caption, not just a plain paragraph that happens to follow an
    intentionally uncaptioned image (`![](path.png)`, no alt text, no
    caption paragraph emitted at all).

    For each match, this replaces the caption paragraph's content with:
        Figure {STYLEREF 2 \\s}.{SEQ Figure \\* ARABIC \\s 2} - Description.
    styled "Caption", so the chapter number is tied live to the nearest
    Heading 2 and the running figure count resets at each Heading 2
    boundary - both computed by Word itself, not this script. The exact
    field-code syntax here was extracted from a caption Word's own
    Insert Caption feature generated (see FIGURE_CAPTION_TEST.docx),
    rather than hand-derived, since a subtly wrong field switch would
    silently fail inside Word.
    """
    doc = Document(docx_file)

    count = 0
    for para in doc.paragraphs:
        if para.style is None or para.style.name != 'Image Caption':
            continue

        description = para.text.strip()

        for run in list(para.runs):
            run._element.getparent().remove(run._element)

        para.style = doc.styles['Caption']
        para.add_run('Figure ')
        _add_field_simple_run(para, ' STYLEREF 2 \\s ', '1')
        para.add_run('.')
        _add_field_simple_run(para, ' SEQ Figure \\* ARABIC \\s 2 ', '1')
        if description:
            para.add_run(f' - {description}')
        count += 1

    if count:
        doc.save(docx_file)
        print(f"  Converted {count} figure caption(s) to auto-numbered Word captions")

    return count


def set_update_fields_on_open(docx_file):
    """
    Force Word to recalculate all fields (STYLEREF/SEQ figure numbers, TOC
    page numbers, etc.) the moment the document is opened, rather than
    showing this script's cached placeholder values until the user
    manually selects-all-and-presses-F9.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document(docx_file)
    settings = doc.settings.element
    if settings.find(qn('w:updateFields')) is None:
        el = OxmlElement('w:updateFields')
        el.set(qn('w:val'), 'true')
        settings.insert(0, el)
        doc.save(docx_file)


def extract_yaml_and_markdown(md_file):
    """
    Extract YAML front matter and Markdown body from a Markdown file.

    Returns:
        tuple: (yaml_data dict, markdown_body str)
    """
    import yaml

    with open(md_file, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    # Check for YAML front matter
    yaml_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(yaml_pattern, content, re.DOTALL)

    if match:
        yaml_text = match.group(1)
        markdown_body = match.group(2)
        yaml_data = yaml.safe_load(yaml_text)
        return yaml_data, markdown_body
    else:
        return {}, content


_TABLE_MARKER_RUN = re.compile(
    r'^(?:[ \t]*@@@TABLE_(?:STYLE:\w+|COLUMNS:[\w.,\s]+)@@@[ \t]*\n)+',
    re.MULTILINE,
)


def _insert_blank_line_if_needed(match):
    already_blank = match.string[match.end():match.end() + 1] == '\n'
    return match.group(0) if already_blank else match.group(0) + '\n'


def ensure_blank_line_after_table_markers(markdown_text):
    """
    Ensure a blank line separates a run of one or more stacked
    @@@TABLE_STYLE:...@@@ / @@@TABLE_COLUMNS:...@@@ marker lines from the
    table that follows them.

    MARKDOWN_STYLING_GUIDE.md documents "no blank lines between the marker
    and the table" as the convention, but Pandoc's pipe-table parser only
    recognizes a table when it is preceded by a blank line - without one,
    the marker line(s) and the entire table are merged into a single
    garbled text paragraph and no table is produced at all. Normalizing
    here (before Pandoc ever sees the markdown) keeps the documented
    authoring convention working while still producing a real, styleable,
    width-settable table.

    Uses a callback (rather than a trailing negative-lookahead assertion)
    to decide whether a blank line already follows the marker run: a
    lookahead combined with the `+` repetition over marker lines can
    backtrack to a *partial* match when the full run is already followed
    by a blank line, inserting a spurious blank line in the middle of a
    stacked marker run instead of leaving it alone.
    """
    return _TABLE_MARKER_RUN.sub(_insert_blank_line_if_needed, markdown_text)


def markdown_to_docx(markdown_text, output_file, reference_doc=None, resource_dir=None):
    """
    Convert Markdown to a Word document using Pandoc.

    Args:
        markdown_text: Markdown content as string
        output_file: Path to save the Word document
        reference_doc: Optional path to reference document for styles
        resource_dir: Optional directory relative image paths in the
            markdown are resolved against (MARKDOWN_STYLING_GUIDE.md
            documents "image path is relative to the markdown file" - this
            is what makes that true regardless of the caller's own cwd).
            Without it, Pandoc resolves relative image paths against the
            process's current working directory, silently embedding a
            placeholder instead of the real image if that happens to
            differ from the markdown file's own directory.
    """
    markdown_text = ensure_blank_line_after_table_markers(markdown_text)

    # Create temporary markdown file
    temp_md = Path(output_file).parent / "_temp_content.md"
    with open(temp_md, 'w', encoding='utf-8') as f:
        f.write(markdown_text)

    # Build Pandoc command
    pandoc_cmd = [
        'pandoc',
        str(temp_md),
        '-o', str(output_file),
        '--standalone',
        '--toc',
        '--toc-depth=6',
        '--from=markdown+smart+backtick_code_blocks+fenced_code_attributes+raw_html',
        '--wrap=preserve'
    ]

    # Add reference document if provided
    if reference_doc:
        pandoc_cmd.extend(['--reference-doc', str(reference_doc)])

    if resource_dir:
        pandoc_cmd.extend(['--resource-path', str(resource_dir)])

    # Use Pandoc to convert Markdown to Word
    try:
        result = subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Pandoc: {e.stderr}")
        raise

    # Pandoc can exit 0 while still warning about problems (e.g. an
    # unresolved image path silently replaced with a placeholder) - surface
    # those warnings even on success instead of only printing on failure.
    if result.stderr:
        print(f"  Pandoc warnings:\n{result.stderr}")

    # Clean up temp file
    temp_md.unlink()


def compose_documents(*doc_paths):
    """
    Merge 2+ Word documents in order via docxcompose's Composer, appending
    each subsequent document to the first.

    Returns the Composer wrapping the merged document - call
    .save(output_path) on the result. Generalizes the compiler's original
    2-document merge_word_documents() to N documents so both the full A-B-C-D
    compile pipeline and the form compiler's 2-document pipeline share one
    implementation.
    """
    composer = Composer(Document(doc_paths[0]))
    for doc_path in doc_paths[1:]:
        composer.append(Document(doc_path))
    return composer
