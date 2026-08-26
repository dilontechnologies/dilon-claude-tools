# -*- coding: utf-8 -*-
"""
Read the current inline-image and table column sizes out of a compiled
Dilon .docx, in document order, so Claude can apply them back onto the
source markdown as {width=...}/{height=...} image attributes and
@@@TABLE_COLUMNS:...@@@ markers.

Usage:
    python read_docx_sizes.py <resized.docx>

Prints a JSON array to stdout. Each image entry:
    {"type": "image", "index": 0, "width_in": 4.06, "height_in": 2.03}
Each table entry:
    {"type": "table", "index": 0, "column_widths_in": [1.5, 3.2, 1.0, 1.0]}

`index` is 0-based and counts only within its own type (image/table),
in document order - it's meant to line up with the Nth image / Nth
table in the source markdown, since neither markdown images nor pipe
tables carry a stable id today. This positional matching breaks if
content was added, removed, or reordered between compiling and
resizing - confirm the image/table counts match the source markdown
before applying any of these values.

The compiled docx also contains the programmatically-generated
signature-approval and revision-history tables, which never appear in
the source markdown - these are detected and excluded (see
classify_table()) so table "index" values line up with body content
only.
"""

import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.shape import WD_INLINE_SHAPE

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

_PICTURE_TYPES = (WD_INLINE_SHAPE.PICTURE, WD_INLINE_SHAPE.LINKED_PICTURE)


def classify_table(table):
    """Return 'signature', 'revision', or 'content' for a python-docx
    Table, based on its first two rows' text (case-insensitive).

    Mirrors dilon-document-extractor's scripts/extract_docx.py
    classify_table() (kept as a separate copy rather than a shared
    import, since that skill lives in its own scripts/ directory) -
    both compose_documents()-assembled parts (the signature-approval
    table and revision-history table) precede any body content in the
    merged docx, so without this filter their widths would be
    misattributed to the markdown's own tables by position."""
    header_text = " ".join(
        cell.text.strip().lower()
        for row in table.rows[:2]
        for cell in row.cells
    )
    if "revision history" in header_text or ("rev #" in header_text and "eco #" in header_text):
        return "revision"
    if "signature" in header_text and ("preparer" in header_text or "name" in header_text):
        return "signature"
    return "content"


def read_sizes(docx_path):
    doc = Document(docx_path)
    results = []

    image_index = 0
    for shape in doc.inline_shapes:
        if shape.type not in _PICTURE_TYPES:
            continue
        results.append({
            "type": "image",
            "index": image_index,
            "width_in": round(shape.width.inches, 2),
            "height_in": round(shape.height.inches, 2),
        })
        image_index += 1

    table_index = 0
    for table in doc.tables:
        if classify_table(table) != "content":
            continue
        widths = [round(col.width.inches, 2) if col.width else None for col in table.columns]
        results.append({
            "type": "table",
            "index": table_index,
            "column_widths_in": widths,
        })
        table_index += 1

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python read_docx_sizes.py <resized.docx>", file=sys.stderr)
        sys.exit(1)

    docx_path = Path(sys.argv[1])
    if not docx_path.exists():
        print(f"Error: file not found: {docx_path}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(read_sizes(docx_path), indent=2))


if __name__ == "__main__":
    main()
