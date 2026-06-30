#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Document from Markdown using Jinja2 Word template in Dilon formatting.

This script:
1. Reads a Word template with Jinja2 variables ({{variable}})
2. Parses Markdown file with YAML front matter
3. Converts Markdown body to Rich Text using python-docx
4. Appends content to the template
5. Generates final Word document

Usage:
    python generate_dilon_doc.py <input.md> <output.docx>

Example:
    python generate_dilon_doc.py MAP-00001_Requirements.md MAP-00001_Requirements.docx
"""

import re
import sys
import yaml
from pathlib import Path
from docxtpl import DocxTemplate
from docxcompose.composer import Composer
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
import subprocess

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
    paragraph_operations = []  # List of (start_idx, end_idx, style_name)
    paragraphs_to_trim = []  # List of (idx, cleaned_text)

    print(f"  🔍 Scanning document with state machine...")

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

            # Handle table style markers (must start the paragraph)
            if text.startswith('@@@TABLE_STYLE:'):
                style_match = re.search(r'@@@TABLE_STYLE:(\w+)@@@', text)
                if style_match:
                    style_name = style_match.group(1)
                    next_element = para._element.getnext()

                    # Check if immediate next element is a table
                    table_found = False
                    if next_element is not None and next_element.tag.endswith('tbl'):
                        # Find the Table object that wraps this XML element
                        for table in doc.tables:
                            if table._element == next_element:
                                table_operations.append((table, style_name))
                                styled_table_elements.add(table._element)
                                table_found = True
                                break

                    if not table_found:
                        print(f"  ⚠️  Table marker '{style_name}' at paragraph {i} not followed by table")

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
        print(f"  ⚠️  Found START marker at paragraph {paragraph_start} but no valid END marker")

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
            print(f"  ⚠️  Could not apply style '{style_name}' to table: {e}")

    # Apply paragraph styles
    for start_idx, end_idx, style_name in paragraph_operations:
        try:
            paras = [doc.paragraphs[k] for k in range(start_idx, end_idx + 1)]
            apply_paragraph_style_to_objects(paras, style_name)
        except Exception as e:
            print(f"  ⚠️  Could not apply style '{style_name}' to paragraphs {start_idx}-{end_idx}: {e}")

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
            # Delete paragraph entirely (marker only)
            paragraphs_to_delete.append(idx)
            p_element = para._element
            p_element.getparent().remove(p_element)

    if paragraphs_to_delete:
        print(f"  ✓ Removed {len(paragraphs_to_delete)} marker paragraph(s)")

    doc.save(docx_file)

def extract_yaml_and_markdown(md_file):
    """
    Extract YAML front matter and Markdown body from a Markdown file.

    Returns:
        tuple: (yaml_data dict, markdown_body str)
    """
    with open(md_file, 'r', encoding='utf-8') as f:
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

def markdown_to_docx(markdown_text, output_file, reference_doc=None):
    """
    Convert Markdown to a Word document using Pandoc.

    Args:
        markdown_text: Markdown content as string
        output_file: Path to save the Word document
        reference_doc: Optional path to reference document for styles
    """
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

    # Use Pandoc to convert Markdown to Word
    try:
        subprocess.run(pandoc_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Pandoc: {e.stderr}")
        raise

    # Clean up temp file
    temp_md.unlink()

def merge_word_documents(frontmatter_doc, content_doc, output_doc):
    """
    Merge two Word documents: frontmatter (template) + content (body).

    Args:
        frontmatter_doc: Path to document with front matter (template output)
        content_doc: Path to document with main content (Pandoc output)
        output_doc: Path to save merged document
    """
    # Load the front matter document
    composer = Composer(Document(frontmatter_doc))

    # Load the content document
    content = Document(content_doc)

    # Append content to front matter
    composer.append(content)

    # Save merged document
    composer.save(output_doc)

def create_revision_table(revisions):
    """
    Create a formatted revision history table as a Word table object.

    Args:
        revisions: List of revision dictionaries with keys: number, description, eco_number, eco_date

    Returns:
        python-docx Table object
    """
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    # Create a temporary document to build the table
    temp_doc = Document()

    # Create table with title + header + data rows
    table = temp_doc.add_table(rows=2 + len(revisions), cols=4)
    table.style = 'Table Grid'

    # Set column widths (in inches): REV # narrow, DESCRIPTION wide, ECO # medium, DATE medium
    table.columns[0].width = Inches(0.6)   # REV # - narrower
    table.columns[1].width = Inches(3.5)   # DESCRIPTION - wider
    table.columns[2].width = Inches(1.0)   # ECO # - medium
    table.columns[3].width = Inches(1.0)   # DATE - medium

    # Title row (row 0) - spans all columns
    title_cell = table.rows[0].cells[0]
    # Merge all cells in first row
    for i in range(1, 4):
        title_cell.merge(table.rows[0].cells[i])
    title_cell.text = "REVISION HISTORY"

    # Format title: bold, centered, gray background
    title_paragraph = title_cell.paragraphs[0]
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title_run = title_paragraph.runs[0]
    title_run.font.bold = True
    title_run.font.size = Pt(11)

    # Set gray background for title
    title_shading = OxmlElement('w:shd')
    title_shading.set(qn('w:fill'), 'C0C0C0')
    title_cell._element.get_or_add_tcPr().append(title_shading)

    # Header row (row 1)
    header_cells = table.rows[1].cells
    headers = ['REV #', 'DESCRIPTION OF CHANGE', 'ECO #', 'DATE']

    for i, header_text in enumerate(headers):
        cell = header_cells[i]
        cell.text = header_text

        # Format header: bold, centered, gray background
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.runs[0]
        run.font.bold = True
        run.font.size = Pt(9)

        # Set gray background
        shading_elm = OxmlElement('w:shd')
        shading_elm.set(qn('w:fill'), 'C0C0C0')
        cell._element.get_or_add_tcPr().append(shading_elm)

    # Data rows (starting at row 2)
    for idx, rev in enumerate(revisions):
        row_cells = table.rows[idx + 2].cells

        # REV #
        row_cells[0].text = rev.get('number', '')
        row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # DESCRIPTION
        row_cells[1].text = rev.get('description', '')

        # ECO #
        row_cells[2].text = rev.get('eco_number', '')
        row_cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

        # DATE
        row_cells[3].text = rev.get('eco_date', '')
        row_cells[3].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Center the table itself using XML
    tbl_pr = table._element.tblPr
    if tbl_pr is None:
        tbl_pr = OxmlElement('w:tblPr')
        table._element.insert(0, tbl_pr)

    # Add table justification element to center the table
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), 'center')
    tbl_pr.append(jc)

    return table

def generate_requirements_document(markdown_path, output_path, signature_template_path=None, content_template_path=None):
    """
    Generate final requirements Word document.

    Args:
        markdown_path: Path to Markdown file with YAML front matter
        output_path: Path to save final Word document
        signature_template_path: Path to signature page template (Part A)
        content_template_path: Path to title/content template (Part C)
    """
    # Default template locations
    script_dir = Path(__file__).parent

    if signature_template_path is None:
        signature_template_path = script_dir / "TEMPLATE_Word_Signature.docx"
    else:
        signature_template_path = Path(signature_template_path)

    if content_template_path is None:
        content_template_path = script_dir / "TEMPLATE_Word_Content.docx"
    else:
        content_template_path = Path(content_template_path)

    if not signature_template_path.exists():
        print(f"❌ Error: Signature template not found: {signature_template_path}")
        sys.exit(1)

    if not content_template_path.exists():
        print(f"❌ Error: Content template not found: {content_template_path}")
        sys.exit(1)

    if not Path(markdown_path).exists():
        print(f"❌ Error: Markdown file not found: {markdown_path}")
        sys.exit(1)

    print(f"📄 Reading Markdown file: {markdown_path}")

    # Extract YAML metadata and Markdown body
    metadata, markdown_body = extract_yaml_and_markdown(markdown_path)

    print(f"✅ Metadata extracted: {list(metadata.keys())}")

    # Step 1: Render Part A (Signature template)
    print(f"📋 Rendering signature page (Part A): {signature_template_path}")
    doc_a = DocxTemplate(signature_template_path)
    doc_a.render(metadata)
    temp_part_a = Path(output_path).parent / "_temp_part_a.docx"
    doc_a.save(temp_part_a)
    print(f"✅ Part A rendered")

    # Step 2: Generate Part B (Revision table)
    temp_part_b = Path(output_path).parent / "_temp_part_b.docx"
    if 'revisions' in metadata and metadata['revisions']:
        print("📊 Building revision history table (Part B)...")
        revision_doc = Document()

        # Create the table
        table = create_revision_table(metadata['revisions'])

        # Center the table before adding to document
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add table to document
        revision_doc._element.body.append(table._element)

        revision_doc.save(temp_part_b)
        print(f"✅ Part B generated")
    else:
        # Create empty document if no revisions
        revision_doc = Document()
        revision_doc.add_paragraph("No revision history available")
        revision_doc.save(temp_part_b)
        print(f"⚠️  No revisions found, created placeholder")

    # Step 3: Render Part C (Content template - title page)
    print(f"📋 Rendering title page (Part C): {content_template_path}")
    doc_c = DocxTemplate(content_template_path)
    doc_c.render(metadata)
    temp_part_c = Path(output_path).parent / "_temp_part_c.docx"
    doc_c.save(temp_part_c)
    print(f"✅ Part C rendered")

    # Step 4: Convert Markdown body to Word (Part D) using signature template as style reference
    print("📝 Converting Markdown content to Word (Part D)...")
    temp_part_d = Path(output_path).parent / "_temp_part_d.docx"

    # Use signature template as reference to ensure consistent formatting across entire document
    markdown_to_docx(markdown_body, temp_part_d, reference_doc=signature_template_path)

    # Apply all styles (tables and paragraphs) - scans Word document for @@@ markers, applies styles, removes markers
    print("🎨 Applying custom styles...")
    apply_styles(temp_part_d)

    print(f"✅ Part D converted")

    # Step 5: Merge all documents in order: A → B → C → D
    print("🔗 Merging all parts (A → B → C → D)...")
    composer = Composer(Document(temp_part_a))
    composer.append(Document(temp_part_b))
    composer.append(Document(temp_part_c))
    composer.append(Document(temp_part_d))
    composer.save(output_path)

    # Clean up temporary files
    temp_part_a.unlink()
    temp_part_b.unlink()
    temp_part_c.unlink()
    temp_part_d.unlink()

    print(f"\n✅ Document generated successfully!")
    print(f"📦 Output: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_requirements_doc.py <input.md> <output.docx> [signature_template.docx] [content_template.docx]")
        print("\nExample:")
        print("  python generate_requirements_doc.py MAP-00001_Requirements.md MAP-00001_Requirements.docx")
        print("  python generate_requirements_doc.py MAP-00001_Requirements.md MAP-00001_Requirements.docx custom_sig.docx custom_content.docx")
        sys.exit(1)

    markdown_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    signature_template_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    content_template_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None

    try:
        generate_requirements_document(markdown_path, output_path, signature_template_path, content_template_path)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
