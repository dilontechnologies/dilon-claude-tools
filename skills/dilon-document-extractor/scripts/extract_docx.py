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
