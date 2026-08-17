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

The Pandoc-conversion and Word-styling helpers this script calls
(apply_styles, apply_figure_captions, markdown_to_docx,
extract_yaml_and_markdown, set_update_fields_on_open, compose_documents)
live in lib/dilon_docx_common.py (repo root) - shared with
dilon-document-form-compiler. See
docs/superpowers/specs/2026-08-17-document-extraction-and-form-tooling-design.md.
"""

import sys
from pathlib import Path
from docxtpl import DocxTemplate
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "lib"))
from dilon_docx_common import (  # noqa: E402
    apply_styles,
    apply_figure_captions,
    markdown_to_docx,
    extract_yaml_and_markdown,
    set_update_fields_on_open,
    compose_documents,
    ensure_blank_line_after_table_markers,
    parse_column_widths,
    apply_table_column_widths,
)


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
        signature_template_path = _REPO_ROOT / "templates" / "TEMPLATE_Word_Signature.docx"
    else:
        signature_template_path = Path(signature_template_path)

    if content_template_path is None:
        content_template_path = _REPO_ROOT / "templates" / "TEMPLATE_Word_Content.docx"
    else:
        content_template_path = Path(content_template_path)

    if not signature_template_path.exists():
        print(f"Error: Signature template not found: {signature_template_path}")
        sys.exit(1)

    if not content_template_path.exists():
        print(f"Error: Content template not found: {content_template_path}")
        sys.exit(1)

    if not Path(markdown_path).exists():
        print(f"Error: Markdown file not found: {markdown_path}")
        sys.exit(1)

    print(f"Reading Markdown file: {markdown_path}")

    # Extract YAML metadata and Markdown body
    metadata, markdown_body = extract_yaml_and_markdown(markdown_path)

    print(f"Metadata extracted: {list(metadata.keys())}")

    # Step 1: Render Part A (Signature template)
    print(f"Rendering signature page (Part A): {signature_template_path}")
    doc_a = DocxTemplate(signature_template_path)
    doc_a.render(metadata)
    temp_part_a = Path(output_path).parent / "_temp_part_a.docx"
    doc_a.save(temp_part_a)
    print(f"Part A rendered")

    # Step 2: Generate Part B (Revision table)
    temp_part_b = Path(output_path).parent / "_temp_part_b.docx"
    if 'revisions' in metadata and metadata['revisions']:
        print("Building revision history table (Part B)...")
        revision_doc = Document()

        # Create the table
        table = create_revision_table(metadata['revisions'])

        # Center the table before adding to document
        table.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Add table to document
        revision_doc._element.body.append(table._element)

        revision_doc.save(temp_part_b)
        print(f"Part B generated")
    else:
        # Create empty document if no revisions
        revision_doc = Document()
        revision_doc.add_paragraph("No revision history available")
        revision_doc.save(temp_part_b)
        print(f"No revisions found, created placeholder")

    # Step 3: Render Part C (Content template - title page)
    print(f"Rendering title page (Part C): {content_template_path}")
    doc_c = DocxTemplate(content_template_path)
    doc_c.render(metadata)
    temp_part_c = Path(output_path).parent / "_temp_part_c.docx"
    doc_c.save(temp_part_c)
    print(f"Part C rendered")

    # Step 4: Convert Markdown body to Word (Part D) using signature template as style reference
    print("Converting Markdown content to Word (Part D)...")
    temp_part_d = Path(output_path).parent / "_temp_part_d.docx"

    # Use signature template as reference to ensure consistent formatting across entire document
    markdown_to_docx(
        markdown_body, temp_part_d,
        reference_doc=signature_template_path,
        resource_dir=Path(markdown_path).resolve().parent,
    )

    # Apply all styles (tables and paragraphs) - scans Word document for @@@ markers, applies styles, removes markers
    print("Applying custom styles...")
    apply_styles(temp_part_d)

    # Convert Pandoc's implicit-figure captions into auto-numbered Word captions
    print("Applying figure caption numbering...")
    apply_figure_captions(temp_part_d)

    print(f"Part D converted")

    # Step 5: Merge all documents in order: A -> B -> C -> D
    print("Merging all parts (A -> B -> C -> D)...")
    composer = compose_documents(temp_part_a, temp_part_b, temp_part_c, temp_part_d)
    composer.save(output_path)

    # Ensure figure numbers / TOC page numbers are correct the moment the
    # document is opened, rather than showing cached placeholder text
    set_update_fields_on_open(output_path)

    # Clean up temporary files
    temp_part_a.unlink()
    temp_part_b.unlink()
    temp_part_c.unlink()
    temp_part_d.unlink()

    print(f"\nDocument generated successfully!")
    print(f"Output: {output_path}")


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
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
