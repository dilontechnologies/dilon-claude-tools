# -*- coding: utf-8 -*-
"""
Auto-numbered, cross-referenceable @@@STEPS@@@ list support for
dilon-document-compiler. See
docs/superpowers/specs/2026-08-20-work-instruction-step-numbering-design.md.

Scoped to dilon-document-compiler only - not shared with
dilon-document-form-compiler (forms have no procedural-steps concept).
"""

import re
import sys
import zipfile
from pathlib import Path

from lxml import etree
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from dilon_docx_common import (
    add_complex_field,
    add_field_simple_run,
    _decimal_abstract_num_ids,
    _num_id_to_abstract_map,
    _paragraph_num_id_and_ilvl,
)

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def get_step_list_abstract_num_id(template_path):
    """
    Reads template_path's numbering.xml/document.xml/styles.xml directly
    (python-docx has no numbering API) to find the abstractNumId backing
    the 'Dilon Step List' style (see the design spec's Template
    Requirement section).

    Checks two places, in order: a sample paragraph in the template body
    using the 'Dilon Step List' style with a numPr applied directly to
    the paragraph, OR - since Word may instead bake the numbering link
    into the style definition itself rather than writing a per-paragraph
    override (confirmed against the real template) - the style's own
    numPr.

    Returns the abstractNumId as a string, or None (with a printed
    warning) if the template doesn't have the style set up yet - callers
    treat None as "skip step-numbering for this compile" rather than
    failing the whole document.
    """
    with zipfile.ZipFile(template_path) as z:
        doc_xml = etree.fromstring(z.read('word/document.xml'))
        styles_xml = etree.fromstring(z.read('word/styles.xml'))
        if 'word/numbering.xml' not in z.namelist():
            print("  Warning: template has no numbering.xml; step numbering skipped")
            return None
        num_xml = etree.fromstring(z.read('word/numbering.xml'))

    sample_num_id = None
    for p in doc_xml.iter(f'{{{W_NS}}}p'):
        p_style = p.find(f'.//{{{W_NS}}}pStyle')
        if p_style is None or p_style.get(f'{{{W_NS}}}val') != 'DilonStepList':
            continue
        num_id_el = p.find(f'.//{{{W_NS}}}numPr/{{{W_NS}}}numId')
        if num_id_el is not None:
            sample_num_id = num_id_el.get(f'{{{W_NS}}}val')
            break

    if sample_num_id is None:
        # Fall back to the style's own numPr.
        for s in styles_xml.iter(f'{{{W_NS}}}style'):
            if s.get(f'{{{W_NS}}}styleId') != 'DilonStepList':
                continue
            num_id_el = s.find(f'.//{{{W_NS}}}pPr/{{{W_NS}}}numPr/{{{W_NS}}}numId')
            if num_id_el is not None:
                sample_num_id = num_id_el.get(f'{{{W_NS}}}val')
            break

    if sample_num_id is None:
        print(
            "  Warning: no paragraph in the base template uses the 'Dilon "
            "Step List' style with numbering applied (checked both the "
            "paragraph and the style itself); step numbering skipped. See "
            "the Template Requirement section of "
            "docs/superpowers/specs/2026-08-20-work-instruction-step-numbering-design.md"
        )
        return None

    for num in num_xml.iter(f'{{{W_NS}}}num'):
        if num.get(f'{{{W_NS}}}numId') == sample_num_id:
            return num.find(f'{{{W_NS}}}abstractNumId').get(f'{{{W_NS}}}val')

    print(f"  Warning: numId {sample_num_id} has no matching <w:num> entry; step numbering skipped")
    return None


def create_num_instance(numbering_element, abstract_num_id):
    """
    Appends a new <w:num> instance to numbering_element (a docx's
    <w:numbering> root, e.g. doc.part.numbering_part.element) referencing
    abstract_num_id, with a numId guaranteed not to collide with any numId
    already present (Pandoc allocates its own numIds for ordinary
    markdown lists in the same document - this must never reuse one of
    those). Returns the new numId as an int.

    Also writes a <w:lvlOverride>/<w:startOverride val="1"> for every
    level 0-8, forcing this instance to start counting at 1 regardless of
    what else in the document already used abstract_num_id. Without this,
    Word continues a level's counter across separate numId instances that
    share the same abstractNumId (confirmed against the real template:
    the throwaway 'Dilon Step List' sample paragraph's own numId bled its
    count into a freshly-allocated numId sharing the same abstract list,
    rendering 2/3/4 instead of 1/2/3) - every NEW step-list sequence must
    start fresh regardless of prior usage elsewhere in the document.
    """
    existing_ids = [int(n.get(qn('w:numId'))) for n in numbering_element.findall(qn('w:num'))]
    new_num_id = max(existing_ids, default=0) + 1

    num_el = OxmlElement('w:num')
    num_el.set(qn('w:numId'), str(new_num_id))
    abstract_ref_el = OxmlElement('w:abstractNumId')
    abstract_ref_el.set(qn('w:val'), str(abstract_num_id))
    num_el.append(abstract_ref_el)

    for ilvl in range(9):
        lvl_override = OxmlElement('w:lvlOverride')
        lvl_override.set(qn('w:ilvl'), str(ilvl))
        start_override = OxmlElement('w:startOverride')
        start_override.set(qn('w:val'), '1')
        lvl_override.append(start_override)
        num_el.append(lvl_override)

    numbering_element.append(num_el)

    return new_num_id


class StepBlockError(ValueError):
    """Raised for a malformed @@@STEPS@@@/@@@END_STEPS@@@ pairing - an
    @@@STEPS@@@ with no matching @@@END_STEPS@@@ before the next
    @@@STEPS@@@ or the end of the document, or an @@@END_STEPS@@@ with
    no @@@STEPS@@@ open. Unlike the old markdown-level version of this
    error, this is now raised post-conversion (see
    apply_section_scoped_step_numbering()) and halts compilation - a
    malformed steps block is an authoring mistake worth surfacing
    clearly, not silently degrading."""


def ensure_blank_line_around_steps_markers(markdown_text):
    """
    Ensures a blank line separates @@@STEPS@@@ from the list that
    follows it, and separates @@@END_STEPS@@@ from the list item that
    precedes it. Both markers now pass through to Pandoc as literal
    paragraphs (no more markdown-level block extraction -
    apply_section_scoped_step_numbering() finds them post-conversion),
    so a marker directly adjacent to a list item with no blank line
    risks CommonMark treating it as a lazy-continuation of that list
    item's own paragraph text instead of a separate paragraph -
    silently corrupting both the step text and the marker detection.

    Implemented as a line-by-line scan rather than the single-regex
    style of ensure_blank_line_after_table_markers()/
    ensure_blank_line_after_list_continue_markers(), because this is
    the one marker in this codebase that needs a blank line inserted
    *before* it (for @@@END_STEPS@@@), not just after - a single
    regex substitution reads and inserts in one direction only.
    """
    lines = markdown_text.split('\n')
    result = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_open = stripped == '@@@STEPS@@@'
        is_close = stripped == '@@@END_STEPS@@@'

        if is_close and result and result[-1].strip() != '':
            result.append('')

        result.append(line)

        if is_open and i + 1 < len(lines) and lines[i + 1].strip() != '':
            result.append('')

    return '\n'.join(result)


def apply_section_scoped_step_numbering(docx_file, abstract_num_id):
    """
    Walks docx_file's paragraphs once, in document order, tracking
    which Heading-2-numbered section each paragraph falls under and
    whether a @@@STEPS@@@ block is currently open. Every #.-list
    paragraph (numFmt="decimal" - see dilon_docx_common's
    _decimal_abstract_num_ids()) found inside an open @@@STEPS@@@
    block gets its numId reassigned to a section-scoped numId,
    allocated fresh the first time a steps block appears in a new
    section and reused automatically for every later steps block in
    that same section - this is what makes cross-block continuation
    within a section automatic, with no marker needed. A #.-list
    paragraph outside any @@@STEPS@@@ block is left completely alone
    (it's an ordinary ordered-list paragraph, already handled by
    remap_ordered_lists_to_dilon_step_list() in the ordered-lists
    plan).

    Both wrapper marker paragraphs are removed from the output
    regardless of whether numbering was actually applied (mirrors
    apply_step_numbering()'s old warn-and-degrade convention: if
    abstract_num_id is None - get_step_list_abstract_num_id() already
    printed a warning that the template isn't set up - step text still
    ships as plain unnumbered text rather than leaving raw
    "@@@STEPS@@@" markers visible in the shipped document).

    Raises StepBlockError for an @@@STEPS@@@ with no matching
    @@@END_STEPS@@@, or an @@@END_STEPS@@@ with no @@@STEPS@@@ open -
    both compilation-halting, not degrade-and-continue, since a
    malformed wrapper pair means the author's procedure boundaries
    don't mean what they look like.
    """
    from docx import Document
    doc = Document(docx_file)
    numbering_part = doc.part.numbering_part if abstract_num_id is not None else None
    numbering_element = numbering_part.element if numbering_part is not None else None

    decimal_ids = _decimal_abstract_num_ids(numbering_element) if numbering_element is not None else set()
    num_id_to_abstract = _num_id_to_abstract_map(numbering_element) if numbering_element is not None else {}

    section_index = 0
    section_num_id = {}  # section_index -> numId currently assigned to that section's steps
    inside_steps = False
    marker_elements = []
    numbered = 0

    for para in doc.paragraphs:
        stripped = para.text.strip()

        if para.style is not None and para.style.name and para.style.name.startswith('Heading 2'):
            section_index += 1
            continue

        if stripped == '@@@STEPS@@@':
            if inside_steps:
                raise StepBlockError("@@@STEPS@@@ opened again before the previous block's @@@END_STEPS@@@")
            inside_steps = True
            marker_elements.append(para._p)
            continue

        if stripped == '@@@END_STEPS@@@':
            if not inside_steps:
                raise StepBlockError("@@@END_STEPS@@@ found with no matching @@@STEPS@@@ open")
            inside_steps = False
            marker_elements.append(para._p)
            continue

        if not inside_steps or abstract_num_id is None:
            continue

        num_id, _ = _paragraph_num_id_and_ilvl(para._p)
        if num_id is None or num_id_to_abstract.get(num_id) not in decimal_ids:
            continue

        if section_index not in section_num_id:
            section_num_id[section_index] = create_num_instance(numbering_element, abstract_num_id)
        target_num_id = section_num_id[section_index]

        para.style = doc.styles['Dilon Step List']
        num_pr = para._p.find(qn('w:pPr')).find(qn('w:numPr'))
        num_pr.find(qn('w:numId')).set(qn('w:val'), str(target_num_id))
        numbered += 1

    if inside_steps:
        raise StepBlockError("@@@STEPS@@@ has no matching @@@END_STEPS@@@ before the end of the document")

    for p_el in marker_elements:
        p_el.getparent().remove(p_el)

    if marker_elements or numbered:
        doc.save(docx_file)
        if numbered:
            print(f"  Applied section-scoped step numbering to {numbered} paragraph(s)")
    return numbered


_CODE_FENCE_RE = re.compile(
    r'^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$',
    re.DOTALL | re.MULTILINE,
)


def _code_fence_ranges(markdown_text):
    """
    Returns [(start, end), ...] character spans covering every fenced
    (```/~~~) code block in markdown_text, so callers can skip a
    [](#step:...) reference or {#step:label} anchor that only appears
    inside a code fence as documentation/example text (e.g.
    MARKDOWN_STYLING_GUIDE.md's own worked example) instead of treating
    it as a real marker to process. Matches apply_styles()'s existing
    precedent (lib/dilon_docx_common.py) of skipping 'Verbatim'-styled
    paragraphs for the same reason.
    """
    return [m.span() for m in _CODE_FENCE_RE.finditer(markdown_text)]


def _inside_any_span(spans, pos):
    return any(start <= pos < end for start, end in spans)


_STEP_REF_RE = re.compile(r'\[\]\(#step:([\w-]+)\)')
_STEP_LABEL_RE = re.compile(r'\{#step:([\w-]+)\}')


def preprocess_step_references(markdown_text):
    """
    Replaces every [](#step:label) - an EMPTY-text link to a #step: id -
    with a STEPREF:<label> sentinel, delimited on both sides by U+E000
    (Private Use Area, never occurs in authored markdown) so an
    immediately-adjacent word (e.g. "[](#step:x)Insert the boards" with
    no space) can't be swallowed into the label's [\\w-]+ capture.
    Pandoc passes the sentinel through untouched, for
    resolve_step_references() to later turn into a live Word
    cross-reference field. A reference with real link text, e.g.
    [see this step](#step:label), is intentionally left untouched - only
    the empty-text form is auto-resolved.

    The step's own {#step:label} anchor - e.g. []{#step:label} inline in
    the step's bullet text - needs no preprocessing at all: it's already
    valid Pandoc bracketed-span-with-id syntax, and Pandoc's docx writer
    turns it into a real bookmark on its own (Task 6 verifies this). This
    function does still scan for it, once, only to warn if the same
    label is declared more than once (first occurrence wins, per the
    design's error-handling rule) - this is the one pass both halves of
    the reference syntax already share over the whole document body.
    """
    fence_spans = _code_fence_ranges(markdown_text)

    label_counts = {}
    for label_match in _STEP_LABEL_RE.finditer(markdown_text):
        if _inside_any_span(fence_spans, label_match.start()):
            continue
        label = label_match.group(1)
        label_counts[label] = label_counts.get(label, 0) + 1
    for label, count in label_counts.items():
        if count > 1:
            print(f"  Warning: {{#step:{label}}} declared more than once; the first occurrence wins for any [](#step:{label}) reference")

    def _replace_ref(m):
        if _inside_any_span(fence_spans, m.start()):
            return m.group(0)
        return f'STEPREF:{m.group(1)}'

    return _STEP_REF_RE.sub(_replace_ref, markdown_text)


_STEP_REF_SENTINEL_RE = re.compile('STEPREF:([\\w-]+)')


class StepReferenceError(ValueError):
    """Raised when a [](#step:label) reference has no matching
    {#step:label} anchor, or when the same {#step:label} label is
    declared more than once - both halt compilation rather than
    degrading to visible placeholder text, per this codebase's
    halt-on-broken-reference convention."""


def resolve_step_references(docx_file):
    """
    Finds every STEPREF:<label> sentinel (from
    preprocess_step_references(), unchanged) in docx_file and replaces
    it with a composite live field:

        "Step " + STYLEREF 2 \\s + "-" + REF step:<label> \\r \\h

    - literal "Step ", then the nearest enclosing Heading 2's own live
    section number, then a literal "-", then the step's own natively-
    rendered list number as a hyperlinked cross-reference. This is
    built fresh here rather than reusing a single REF field, because
    the section prefix and the step's own number come from two
    different live sources (STYLEREF off the heading vs. REF \\r off
    the step's own bookmark) that can't be expressed as one field.

    A sentinel whose label has no matching {#step:label} bookmark
    anywhere in the document, or a label declared more than once,
    raises StepReferenceError listing every offending label - this
    replaces the old warn-and-degrade-to-plain-text behavior.
    """
    from docx import Document
    doc = Document(docx_file)
    body = doc.element.body

    bookmark_names = {}
    duplicates = set()
    for el in body.iter(qn('w:bookmarkStart')):
        name = el.get(qn('w:name'))
        if not (name and name.startswith('step:')):
            continue
        if name in bookmark_names:
            duplicates.add(name)
        bookmark_names[name] = True

    if duplicates:
        raise StepReferenceError(
            "duplicate {#step:...} anchor(s): "
            + ", ".join(repr(d.split(':', 1)[1]) for d in sorted(duplicates))
        )

    missing = []
    resolved = 0

    for para in doc.paragraphs:
        matches = list(_STEP_REF_SENTINEL_RE.finditer(para.text))
        if not matches:
            continue

        original_text = para.text
        for run in list(para.runs):
            run._element.getparent().remove(run._element)

        cursor = 0
        for match in matches:
            before_text = original_text[cursor:match.start()]
            if before_text:
                para.add_run(before_text)

            label = match.group(1)
            bookmark_name = f'step:{label}'
            if bookmark_name in bookmark_names:
                para.add_run('Step ')
                add_field_simple_run(para, ' STYLEREF 2 \\s ', '1')
                para.add_run('-')
                add_complex_field(para, f'REF {bookmark_name} \\r \\h', '1')
                resolved += 1
            else:
                missing.append(label)

            cursor = match.end()

        trailing_text = original_text[cursor:]
        if trailing_text:
            para.add_run(trailing_text)

    if missing:
        raise StepReferenceError(
            "no matching {#step:...} anchor for: " + ", ".join(repr(m) for m in missing)
        )

    if resolved:
        doc.save(docx_file)
        print(f"  Resolved {resolved} step reference(s)")
