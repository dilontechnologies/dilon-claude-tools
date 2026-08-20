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
from dilon_docx_common import add_complex_field

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


_CODE_FENCE_RE = re.compile(
    r'^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$',
    re.DOTALL | re.MULTILINE,
)


def _code_fence_ranges(markdown_text):
    """
    Returns [(start, end), ...] character spans covering every fenced
    (```/~~~) code block in markdown_text, so callers can skip a
    @@@STEPS@@@/[](#step:...) marker that only appears inside a code
    fence as documentation/example text (e.g.
    MARKDOWN_STYLING_GUIDE.md's own worked example) instead of treating
    it as a real marker to process. Matches apply_styles()'s existing
    precedent (lib/dilon_docx_common.py) of skipping 'Verbatim'-styled
    paragraphs for the same reason.
    """
    return [m.span() for m in _CODE_FENCE_RE.finditer(markdown_text)]


def _inside_any_span(spans, pos):
    return any(start <= pos < end for start, end in spans)


_STEPS_BLOCK_RE = re.compile(
    r'@@@STEPS(?::\s*([^\n@]*?)\s*)?@@@\n(.*?)\n@@@END_STEPS@@@',
    re.DOTALL,
)
_BULLET_LINE_RE = re.compile(r'^(?P<indent>[ \t]*)-[ \t]+(?P<text>.*)$')


class StepBlockError(ValueError):
    """Raised for a malformed @@@STEPS@@@ block; preprocess_steps_markdown
    catches this and leaves the block completely untouched in the output,
    per the design's warn-and-degrade convention."""


def _parse_attribute(attr_text):
    attr_text = (attr_text or '').strip()
    if not attr_text:
        return ('new', None)
    if attr_text == 'continue':
        return ('continue', None)
    match = re.match(r'^continue\s*=\s*(\S+)$', attr_text)
    if match:
        return ('continue_named', match.group(1))
    match = re.match(r'^id\s*=\s*(\S+)$', attr_text)
    if match:
        return ('new_named', match.group(1))
    raise StepBlockError(f"unrecognized @@@STEPS@@@ attribute: {attr_text!r}")


def _parse_bullet_lines(block_body):
    """Returns [(depth, text), ...], one per bullet line. 2-space
    indentation per nesting level, matching MARKDOWN_STYLING_GUIDE.md's
    existing nested-list convention. Raises StepBlockError for any
    non-blank, non-bullet line (including a wrapped continuation line with
    no leading '-') or an empty block."""
    lines = []
    for raw_line in block_body.split('\n'):
        if not raw_line.strip():
            continue
        match = _BULLET_LINE_RE.match(raw_line)
        if not match:
            raise StepBlockError(f"non-bullet line inside @@@STEPS@@@ block: {raw_line!r}")
        indent = match.group('indent').replace('\t', '  ')
        if len(indent) % 2 != 0:
            raise StepBlockError(f"odd indentation ({len(indent)} spaces) inside @@@STEPS@@@ block: {raw_line!r}")
        lines.append((len(indent) // 2, match.group('text')))
    if not lines:
        raise StepBlockError("@@@STEPS@@@ block has no bullet items")
    return lines


def preprocess_steps_markdown(markdown_text):
    """
    Resolves every @@@STEPS...@@@ ... @@@END_STEPS@@@ block in document
    order: strips the wrapper markers, tags each bullet line with an
    invisible STEP<idx> sentinel, and returns
    (new_markdown_text, manifest) where manifest[idx] is
    {'sequence_key': str, 'depth': int} for the step line carrying
    sentinel index idx.

    A block that fails to parse (StepBlockError) is left completely
    untouched in the output, markers included - apply_step_numbering()
    later only ever looks for sentinels, so an unprocessed block's
    literal @@@STEPS@@@ text just passes through Pandoc as plain
    paragraph text. This is the documented warn-and-degrade fallback.
    """
    manifest = []
    most_recent_key = None
    named_keys_seen = set()
    unnamed_counter = 0
    output_parts = []
    cursor = 0
    warnings = []

    fence_spans = _code_fence_ranges(markdown_text)

    for match in _STEPS_BLOCK_RE.finditer(markdown_text):
        output_parts.append(markdown_text[cursor:match.start()])
        cursor = match.end()

        if _inside_any_span(fence_spans, match.start()):
            # A @@@STEPS@@@ block shown as a code-fenced documentation
            # example - leave it completely untouched, same as a
            # malformed block, but without a warning since this is
            # expected/intentional.
            output_parts.append(match.group(0))
            continue

        try:
            kind, name = _parse_attribute(match.group(1))
            bullet_lines = _parse_bullet_lines(match.group(2))
        except StepBlockError as exc:
            warnings.append(str(exc))
            output_parts.append(match.group(0))
            continue

        if kind == 'new':
            unnamed_counter += 1
            sequence_key = f'__unnamed_{unnamed_counter}__'
        elif kind == 'new_named':
            if name in named_keys_seen:
                warnings.append(f"@@@STEPS: id={name}@@@ declared more than once; treating as a fresh sequence")
            named_keys_seen.add(name)
            sequence_key = name
        elif kind == 'continue':
            if most_recent_key is None:
                warnings.append("@@@STEPS: continue@@@ has nothing earlier to continue; starting fresh")
                unnamed_counter += 1
                sequence_key = f'__unnamed_{unnamed_counter}__'
            else:
                sequence_key = most_recent_key
        else:  # continue_named
            if name not in named_keys_seen:
                warnings.append(f"@@@STEPS: continue={name}@@@ names a sequence that was never declared; starting fresh")
                named_keys_seen.add(name)
            sequence_key = name

        most_recent_key = sequence_key

        rebuilt_lines = []
        for depth, text in bullet_lines:
            idx = len(manifest)
            manifest.append({'sequence_key': sequence_key, 'depth': depth})
            rebuilt_lines.append('  ' * depth + f'- STEP{idx}{text}')
        output_parts.append('\n'.join(rebuilt_lines))

    output_parts.append(markdown_text[cursor:])

    for warning in warnings:
        print(f"  Warning: {warning}")

    return ''.join(output_parts), manifest


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


_STEP_SENTINEL_RE = re.compile('\uE000STEP(' + r'\d+' + ')\uE000')


def _run_containing_span(paragraph, start, end):
    """
    Returns (run, local_start, local_end) if the character span
    [start, end) of paragraph.text falls entirely within one run's own
    text, else None. Lets a sentinel be stripped by editing just that
    run's text in place - preserving every other run's formatting -
    instead of clearing and rebuilding the whole paragraph as one plain
    run (which silently destroys any inline bold/italic elsewhere in the
    paragraph's text).
    """
    offset = 0
    for run in paragraph.runs:
        run_len = len(run.text)
        if offset <= start and end <= offset + run_len:
            return run, start - offset, end - offset
        offset += run_len
    return None


def _strip_sentinel_from_paragraph(paragraph, match):
    """
    Removes match's span from paragraph's visible text. If the sentinel
    lies entirely within one run, edits just that run's text (preserving
    every other run's formatting). Falls back to clearing and rebuilding
    the whole paragraph as one plain run only if the sentinel
    unexpectedly spans multiple runs (not expected in practice - the
    sentinel is always inserted as one contiguous piece of plain text
    with no markdown formatting of its own).
    """
    located = _run_containing_span(paragraph, match.start(), match.end())
    if located is not None:
        run, local_start, local_end = located
        run.text = run.text[:local_start] + run.text[local_end:]
        return

    cleaned_text = paragraph.text[:match.start()] + paragraph.text[match.end():]
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)
    paragraph.add_run(cleaned_text)


def apply_step_numbering(docx_file, manifest, abstract_num_id):
    """
    Applies the 'Dilon Step List' style + native Word numbering (numId
    per resolved sequence_key, ilvl per nesting depth) to every paragraph
    in docx_file whose text carries a STEP<idx> sentinel (from
    preprocess_steps_markdown()), then strips the sentinel out of that
    paragraph's visible text. Two blocks resolved to the same
    sequence_key get mapped to the SAME numId, which is what makes
    "continue" a real, native, live-updating continuation - Word's
    numbering engine counts by shared numId, not by paragraph adjacency.

    If abstract_num_id is None (a warning has already been printed by
    get_step_list_abstract_num_id() - the template isn't set up yet),
    still strips every sentinel so the step's own text ships as plain
    unnumbered text, matching the warn-and-degrade convention every other
    marker in this codebase follows, rather than leaving the raw
    "STEP0Wear clean gloves." sentinel visible in the shipped document.
    Does nothing if manifest is empty (no @@@STEPS@@@ blocks in this
    document).
    """
    if not manifest:
        return

    from docx import Document
    doc = Document(docx_file)
    numbering_element = doc.part.numbering_part.element if abstract_num_id is not None else None

    key_to_num_id = {}
    matched = 0

    for para in doc.paragraphs:
        match = _STEP_SENTINEL_RE.search(para.text)
        if not match:
            continue

        if abstract_num_id is not None:
            idx = int(match.group(1))
            entry = manifest[idx]
            sequence_key = entry['sequence_key']
            depth = entry['depth']

            if sequence_key not in key_to_num_id:
                key_to_num_id[sequence_key] = create_num_instance(numbering_element, abstract_num_id)
            num_id = key_to_num_id[sequence_key]

            para.style = doc.styles['Dilon Step List']
            p_pr = para._p.get_or_add_pPr()
            # Remove any numPr Pandoc's own default list conversion already added.
            existing_num_pr = p_pr.find(qn('w:numPr'))
            if existing_num_pr is not None:
                p_pr.remove(existing_num_pr)
            num_pr = OxmlElement('w:numPr')
            ilvl_el = OxmlElement('w:ilvl')
            ilvl_el.set(qn('w:val'), str(depth))
            num_id_el = OxmlElement('w:numId')
            num_id_el.set(qn('w:val'), str(num_id))
            num_pr.append(ilvl_el)
            num_pr.append(num_id_el)
            p_pr.append(num_pr)

        _strip_sentinel_from_paragraph(para, match)

        matched += 1

    if matched:
        doc.save(docx_file)
        if abstract_num_id is not None:
            print(f"  Applied native step numbering to {matched} paragraph(s) across {len(key_to_num_id)} sequence(s)")


_STEP_REF_SENTINEL_RE = re.compile('STEPREF:([\\w-]+)')


def resolve_step_references(docx_file):
    """
    Finds every STEPREF:<label> sentinel (from
    preprocess_step_references()) in docx_file and replaces it with a
    live Word cross-reference field (REF <bookmark> \\r \\h - the same
    field Word's own Insert -> Cross-reference -> Numbered item inserts)
    targeting the {#step:label} bookmark Pandoc already created. A
    sentinel whose label has no matching bookmark anywhere in the
    document degrades to visible plain text
    "[missing step reference: <label>]" rather than failing the compile.
    If two bookmarks share the same name, the first one found in
    document order wins.
    """
    from docx import Document
    doc = Document(docx_file)
    body = doc.element.body

    bookmark_names = {
        el.get(qn('w:name'))
        for el in body.iter(qn('w:bookmarkStart'))
    }

    resolved = 0
    missing = 0

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
                add_complex_field(para, f'REF {bookmark_name} \\r \\h', '1')
                resolved += 1
            else:
                para.add_run(f'[missing step reference: {label}]')
                print(f"  Warning: step reference to unknown label '{label}'; left as visible plain text")
                missing += 1

            cursor = match.end()

        trailing_text = original_text[cursor:]
        if trailing_text:
            para.add_run(trailing_text)

    if resolved or missing:
        doc.save(docx_file)
        print(f"  Resolved {resolved} step reference(s), {missing} missing")
