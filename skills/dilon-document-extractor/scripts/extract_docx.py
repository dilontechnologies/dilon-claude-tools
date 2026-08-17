"""Extract a Dilon-style .docx into a best-effort Dilon markdown draft.

See docs/superpowers/specs/2026-08-17-document-extraction-and-form-tooling-design.md
(dilon-claude-tools repo) for the design this implements.
"""

import re
import sys
from pathlib import Path

WORD_HEADING_RE = re.compile(r'^Heading (\d)$')
SUSPICIOUS_WORD_COUNT_THRESHOLD = 12


def word_heading_level(style_name):
    """Return the numeric Word heading level (1-9) for a paragraph style
    name like 'Heading 2', or None if style_name isn't a heading style."""
    if not style_name:
        return None
    m = WORD_HEADING_RE.match(style_name)
    return int(m.group(1)) if m else None


def compute_heading_shift(doc):
    """Scan every paragraph in doc and return the shift to add to a Word
    heading level to get its markdown '#' count, such that the shallowest
    heading level present maps to 2 (markdown '##', matching the
    compiler's H2-is-top convention). Returns 2 (no-op shift for a
    document with no headings, since level + 2 would be wrong - callers
    only use the shift when a heading is actually present)."""
    levels = [
        word_heading_level(p.style.name if p.style else None)
        for p in doc.paragraphs
    ]
    levels = [lvl for lvl in levels if lvl is not None]
    if not levels:
        return 2
    return 2 - min(levels)


def markdown_heading_prefix(word_level, shift):
    """Return the '#'*N markdown heading prefix for a Word heading level,
    given the shift computed by compute_heading_shift(). Clamped to
    markdown's practical range (## through ######)."""
    n = max(2, min(word_level + shift, 6))
    return '#' * n


def is_suspicious_heading_text(text):
    """True if a heading-styled paragraph reads like body text rather than
    a real heading (ends in a period, or unusually long) - flagged for
    human review, never silently rewritten."""
    text = text.strip()
    if not text:
        return False
    if text.endswith('.'):
        return True
    return len(text.split()) > SUSPICIOUS_WORD_COUNT_THRESHOLD


ROLE_LABEL_HINTS = {
    "regulatory_rep": ("regulat",),
    "quality_rep": ("quality", "qa", "qc"),
    "department_head": ("head", "director", "manager"),
}
# Position of each role's data row within the canonical 6-row signature
# table shape (see TEMPLATE_Word_Signature.docx): row 1 is
# department/author, rows 3-5 are regulatory/quality/department_head.
SIGNATURE_ROLE_ROW_ORDER = ["regulatory_rep", "quality_rep", "department_head"]


def classify_table(table):
    """Return 'signature', 'revision', or 'content' for a python-docx
    Table, based on its first two rows' text (case-insensitive)."""
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


def extract_signature_fields(table):
    """table: a Table classified as 'signature'. Returns (fields, warnings).
    fields may include 'author', 'department', 'regulatory_rep',
    'quality_rep', 'department_head'. Matches TEMPLATE_Word_Signature.docx's
    canonical 6-row shape by position, cross-checked against each row's
    label text where recognizable - a warning (not a failure) is returned
    for any row whose label doesn't match its expected canonical wording,
    since real source documents (e.g. WI-00077) use inconsistent role
    labels ("R&D / Eng", "Manufacturing") in these slots."""
    fields = {}
    warnings = []
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]

    if len(rows) < 6:
        warnings.append(
            f"signature table has {len(rows)} rows, expected 6 (canonical "
            "Group/Preparer/Signature + Department/Name/Signature shape) "
            "- extracted nothing, fill approvers in manually"
        )
        return fields, warnings

    fields["department"] = rows[1][0]
    fields["author"] = rows[1][1]

    for row, expected_role in zip(rows[3:6], SIGNATURE_ROLE_ROW_ORDER):
        label, value = row[0], row[1]
        fields[expected_role] = value
        hints = ROLE_LABEL_HINTS[expected_role]
        # department_head rows are commonly labeled with the department
        # name itself (e.g. "Engineering") rather than a role word.
        label_matches_department = (
            expected_role == "department_head"
            and label.strip().lower() == fields["department"].strip().lower()
        )
        if not label_matches_department and not any(hint in label.lower() for hint in hints):
            warnings.append(
                f"row labeled '{label}' assigned to {expected_role} by "
                "table position (label didn't match expected wording) - verify"
            )

    return fields, warnings


def extract_revisions(table):
    """table: a Table classified as 'revision'. Returns a list of dicts
    with keys 'number', 'description', 'eco_number', 'eco_date', skipping
    a leading merged 'REVISION HISTORY' title row and the column-header
    row if present."""
    rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
    idx = 0
    if rows and rows[0][0].strip().upper() == "REVISION HISTORY":
        idx = 1
    if idx < len(rows) and rows[idx][:2] == ["REV #", "DESCRIPTION OF CHANGE"]:
        idx += 1

    revisions = []
    for row in rows[idx:]:
        if len(row) < 4 or not row[0].strip():
            continue
        revisions.append({
            "number": row[0].strip(),
            "description": row[1].strip(),
            "eco_number": row[2].strip(),
            "eco_date": row[3].strip(),
        })
    return revisions


DOC_NUMBER_RE = re.compile(r'Number:\s*([A-Za-z]{2,}-\d+)')
REV_RE = re.compile(r'Rev\s+(\d+)')
FOOTER_LINE_RE = re.compile(
    r'([A-Za-z]{2,}-\d+)\s+Rev\s+(\d+)\s+(ECO-\d+)\s+Revision Date:\s*([\d/]+)'
)
FIGURE_PREFIX_RE = re.compile(r'^Figure\s+[\d.]+\s*[:\-]\s*', re.IGNORECASE)


def extract_header_footer_metadata(doc):
    """Returns a dict that may include 'title', 'doc_number',
    'current_revision', 'footer_eco_number', 'footer_eco_date', parsed from
    the document's running header table and footer text - the most
    structured, reliable source for these fields (see the spec's empirical
    findings)."""
    fields = {}
    section = doc.sections[0]

    for table in section.header.tables:
        for row in table.rows:
            joined = " ".join(cell.text.strip() for cell in row.cells)
            m = DOC_NUMBER_RE.search(joined)
            if m:
                fields["doc_number"] = m.group(1)
            m = REV_RE.search(joined)
            if m:
                fields["current_revision"] = m.group(1)

    footer_text = "\n".join(p.text for p in section.footer.paragraphs if p.text.strip())
    m = FOOTER_LINE_RE.search(footer_text)
    if m:
        fields.setdefault("doc_number", m.group(1))
        fields.setdefault("current_revision", m.group(2))
        fields["footer_eco_number"] = m.group(3)
        fields["footer_eco_date"] = m.group(4)

    return fields


def strip_figure_prefix(text):
    """Strip a leading 'Figure N:'/'Figure N.M -' prefix from caption text,
    since the compiler generates that prefix itself from the image's alt
    text (MARKDOWN_STYLING_GUIDE.md SS4.1)."""
    return FIGURE_PREFIX_RE.sub('', text).strip()


def slugify(text, existing=None):
    """Lowercase, hyphenate text into a Pandoc-safe identifier fragment,
    deduplicated against `existing` (a set this function mutates) with a
    -2, -3, ... suffix on collision."""
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or "figure"
    existing = existing if existing is not None else set()
    candidate = slug
    n = 2
    while candidate in existing:
        candidate = f"{slug}-{n}"
        n += 1
    existing.add(candidate)
    return candidate


def paragraph_image_rids(paragraph):
    """Return the r:embed relationship IDs of any inline images in a
    paragraph, in document order."""
    from docx.oxml.ns import qn
    return [
        blip.get(qn('r:embed'))
        for blip in paragraph._p.findall('.//' + qn('a:blip'))
        if blip.get(qn('r:embed'))
    ]


def save_image(doc, rid, images_dir, index):
    """Write the image identified by relationship id `rid` to
    images_dir/imageNN.<ext>, returning the filename (not full path)."""
    part = doc.part.related_parts[rid]
    ext = part.content_type.split('/')[-1].replace('jpeg', 'jpg')
    filename = f"image{index:02d}.{ext}"
    (Path(images_dir) / filename).write_bytes(part.blob)
    return filename
