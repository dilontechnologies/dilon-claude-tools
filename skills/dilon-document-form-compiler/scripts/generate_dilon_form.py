# -*- coding: utf-8 -*-
"""
Generate a Dilon form document (running header/footer only - no title
page, no signature page, no table of contents) from Dilon markdown with
YAML front matter.

Usage:
    python generate_dilon_form.py <input.md> <output.docx> [base_template.docx]
"""

import sys
from pathlib import Path
from docxtpl import DocxTemplate

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "lib"))
from dilon_docx_common import (  # noqa: E402
    extract_yaml_and_markdown,
    render_jinja,
    markdown_to_docx,
    apply_styles,
    compose_documents,
    set_update_fields_on_open,
)

try:
    from form_fields import apply_form_fields
except ImportError:
    apply_form_fields = None


def generate_form_document(markdown_path, output_path, form_template_path=None):
    """
    Generate a form Word document.

    Args:
        markdown_path: Path to Markdown file with YAML front matter
        output_path: Path to save the final Word document
        form_template_path: Path to the header/footer + styles template
            (no signature-approval table) - defaults to the same
            templates/TEMPLATE_Word_Base.docx that dilon-document-compiler
            uses, since neither skill's template carries a body table
            anymore.
    """
    if form_template_path is None:
        form_template_path = _REPO_ROOT / "templates" / "TEMPLATE_Word_Base.docx"
    else:
        form_template_path = Path(form_template_path)

    if not form_template_path.exists():
        print(f"Error: Form template not found: {form_template_path}")
        sys.exit(1)

    if not Path(markdown_path).exists():
        print(f"Error: Markdown file not found: {markdown_path}")
        sys.exit(1)

    print(f"Reading Markdown file: {markdown_path}")
    metadata, markdown_body = extract_yaml_and_markdown(markdown_path)
    markdown_body = render_jinja(markdown_body, metadata)
    print(f"Metadata extracted: {list(metadata.keys())}")

    # Part A: the base template, rendered for its header/footer
    print(f"Rendering form header/footer: {form_template_path}")
    doc_a = DocxTemplate(form_template_path)
    doc_a.render(metadata)
    temp_part_a = Path(output_path).parent / "_temp_form_a.docx"
    doc_a.save(temp_part_a)

    # Part D: the form's own content, no TOC (forms have no heading
    # structure to build one from)
    print("Converting form content to Word...")
    temp_part_d = Path(output_path).parent / "_temp_form_d.docx"
    markdown_to_docx(
        markdown_body, temp_part_d,
        reference_doc=form_template_path,
        resource_dir=Path(markdown_path).resolve().parent,
        include_toc=False,
    )

    print("Applying custom styles...")
    apply_styles(temp_part_d)

    if apply_form_fields is not None:
        print("Applying form-specific field markers...")
        apply_form_fields(temp_part_d)

    print("Merging header/footer with content...")
    composer = compose_documents(temp_part_a, temp_part_d)
    composer.save(output_path)

    set_update_fields_on_open(output_path)

    temp_part_a.unlink()
    temp_part_d.unlink()

    print(f"\nForm document generated successfully!")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_dilon_form.py <input.md> <output.docx> [base_template.docx]")
        sys.exit(1)

    markdown_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    form_template_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    try:
        generate_form_document(markdown_path, output_path, form_template_path)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
