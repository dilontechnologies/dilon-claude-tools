"""Lower-fidelity PDF -> Dilon markdown draft extraction.

Untagged PDFs carry no reliable style/heading metadata, so this path does
NOT attempt heading-level inference (unlike extract_docx.py) - it emits
body text plus any embedded images, with a banner comment telling the
reader to re-derive section structure by hand. See the spec's Non-goals.
"""

import sys
from pathlib import Path

BANNER = (
    "PDF source - heading structure and section breaks were not inferred; "
    "re-derive them by reading the source before treating this as more "
    "than a rough draft"
)


def extract(pdf_path, output_dir):
    """Extract pdf_path into output_dir/<slug>.md plus output_dir/images/.
    Returns {'markdown_path': Path, 'images_dir': Path, 'warnings': list[str]}."""
    import fitz

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    warnings = [BANNER]
    body_lines = []
    image_index = 1

    doc = fitz.open(str(pdf_path))
    try:
        for page in doc:
            text = page.get_text().strip()
            if text:
                body_lines.append(text)
                body_lines.append("")
            for image_ref in page.get_images(full=True):
                xref = image_ref[0]
                base_image = doc.extract_image(xref)
                filename = f"image{image_index:02d}.{base_image['ext']}"
                (images_dir / filename).write_bytes(base_image["image"])
                body_lines.append(f"![](images/{filename})")
                body_lines.append("")
                image_index += 1
    finally:
        doc.close()

    slug = pdf_path.stem.lower().replace(' ', '-')
    md_path = output_dir / f"{slug}.md"

    front_matter = (
        '---\n'
        f'title: "{pdf_path.stem}"\n'
        'author: ""\n'
        'department: ""\n'
        'doc_number: ""\n'
        'current_revision: "00"\n'
        'regulatory_rep: ""\n'
        'quality_rep: ""\n'
        'department_head: ""\n'
        'revisions: []\n'
        '---\n\n'
    )
    comment = f"<!-- EXTRACTOR: {BANNER} -->\n\n"
    body_text = "\n".join(body_lines).strip() + "\n"

    md_path.write_text(front_matter + comment + body_text, encoding="utf-8")

    return {"markdown_path": md_path, "images_dir": images_dir, "warnings": warnings}


def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_pdf.py <input.pdf> <output_dir>")
        return 1
    result = extract(sys.argv[1], sys.argv[2])
    print(f"Wrote {result['markdown_path']}")
    for w in result["warnings"]:
        print(f"[WARN] {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
