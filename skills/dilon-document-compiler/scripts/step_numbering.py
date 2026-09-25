# -*- coding: utf-8 -*-
"""
@@@STEPS@@@ procedure-step support for dilon-document-compiler.

Steps compile to real Word list items on the headings' own multilevel
list (one level below Heading 3), so Word itself numbers them
"<H2>.<H3>.<step>", restarts them at every Heading 3, and adds the next
step when a user presses Enter after one. Two passes:

- apply_step_list_numbering() - before the docxcompose merge: removes the
  @@@STEPS@@@ markers, restyles steps 'Dilon Step Heading' (with NO list
  numbering yet), reletters ordered clarifications, and enforces the
  block/heading rules.
- link_steps_to_heading_numbering() - after the merge: attaches every step
  to the heading list. This must run post-merge because docxcompose remaps
  paragraph-level numIds into a copied, separate list.

Design: docs/superpowers/specs/2026-09-25-steps-native-list-numbering-design.md
(deleted from the tree once executed - recover it from git history).
"""

import sys
import zipfile
from pathlib import Path

from lxml import etree
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from dilon_docx_common import (
    add_complex_field,
    _decimal_abstract_num_ids,
    _num_id_to_abstract_map,
    _paragraph_num_id_and_ilvl,
)

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def get_step_clarification_abstract_num_id(template_path):
    """
    Reads template_path's numbering.xml/document.xml/styles.xml directly
    to find the abstractNumId backing the 'Dilon Step Clarification
    List' style - the lowerLetter list ordered clarifications inside
    @@@STEPS@@@ get relettered onto, one fresh instance per step. Same
    two-place lookup as the retired get_step_list_abstract_num_id():
    a sample paragraph using the style with a numPr override, or the
    style's own baked-in numPr.

    Returns the abstractNumId as a string, or None (with a printed
    warning) if the template doesn't have the style set up - callers
    treat None as "leave ordered clarifications alone for this
    compile" rather than failing the whole document.
    """
    with zipfile.ZipFile(template_path) as z:
        doc_xml = etree.fromstring(z.read('word/document.xml'))
        styles_xml = etree.fromstring(z.read('word/styles.xml'))
        if 'word/numbering.xml' not in z.namelist():
            print("  Warning: template has no numbering.xml; step clarification numbering skipped")
            return None
        num_xml = etree.fromstring(z.read('word/numbering.xml'))

    sample_num_id = None
    for p in doc_xml.iter(f'{{{W_NS}}}p'):
        p_style = p.find(f'.//{{{W_NS}}}pStyle')
        if p_style is None or p_style.get(f'{{{W_NS}}}val') != 'DilonStepClarificationList':
            continue
        num_id_el = p.find(f'.//{{{W_NS}}}numPr/{{{W_NS}}}numId')
        if num_id_el is not None:
            sample_num_id = num_id_el.get(f'{{{W_NS}}}val')
            break

    if sample_num_id is None:
        for s in styles_xml.iter(f'{{{W_NS}}}style'):
            if s.get(f'{{{W_NS}}}styleId') != 'DilonStepClarificationList':
                continue
            num_id_el = s.find(f'.//{{{W_NS}}}pPr/{{{W_NS}}}numPr/{{{W_NS}}}numId')
            if num_id_el is not None:
                sample_num_id = num_id_el.get(f'{{{W_NS}}}val')
            break

    if sample_num_id is None:
        print(
            "  Warning: no paragraph in the base template uses the 'Dilon "
            "Step Clarification List' style with numbering applied; "
            "step clarification numbering skipped. See "
            "docs/superpowers/specs/2026-08-24-steps-field-numbering-design.md"
        )
        return None

    for num in num_xml.iter(f'{{{W_NS}}}num'):
        if num.get(f'{{{W_NS}}}numId') == sample_num_id:
            return num.find(f'{{{W_NS}}}abstractNumId').get(f'{{{W_NS}}}val')

    print(f"  Warning: numId {sample_num_id} has no matching <w:num> entry; step clarification numbering skipped")
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
    """Raised for malformed @@@STEPS@@@ usage - an unmatched or reopened
    marker, a block left open across a section heading, a block with no
    Heading 3 above it, or a Heading 3 mixing a Heading 4 with a block.
    Raised post-conversion by apply_step_list_numbering(); see its
    docstring for the full list of conditions. Halts compilation - a
    malformed steps block is an authoring mistake worth surfacing
    clearly, not silently degrading."""


def ensure_blank_line_around_steps_markers(markdown_text):
    """
    Ensures a blank line separates @@@STEPS@@@ from the list that
    follows it, and separates @@@END_STEPS@@@ from the list item that
    precedes it. Both markers now pass through to Pandoc as literal
    paragraphs (no more markdown-level block extraction -
    apply_step_list_numbering() finds them post-conversion),
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


def _strip_num_pr(p_element):
    """Removes <w:numPr> from p_element's <w:pPr>, if present - used to
    turn a step's paragraph from a list item into plain text before
    restyling it 'Dilon Step Heading' (the list link is re-added post-merge
    by link_steps_to_heading_numbering())."""
    p_pr = p_element.find(qn('w:pPr'))
    if p_pr is None:
        return
    num_pr = p_pr.find(qn('w:numPr'))
    if num_pr is not None:
        p_pr.remove(num_pr)


def _decrement_bullet_ilvl(p_element, ilvl):
    """Shifts a bullet-list paragraph's <w:numPr>/<w:ilvl> up by one level
    (e.g. ilvl 2 -> 1), leaving its numId untouched. Compensates for the
    step it's nested under no longer being a real list item: Pandoc
    still assigns ilvl based on the *original* markdown nesting depth,
    which counted the step itself as level 0, so every bullet inside
    @@@STEPS@@@ renders one level deeper than it should once the step's
    own level is stripped out. A bullet already at ilvl 0 (nested
    directly under nothing - shouldn't normally occur inside a block)
    is left alone rather than going negative."""
    if ilvl in (None, '0'):
        return
    num_pr = p_element.find(qn('w:pPr')).find(qn('w:numPr'))
    ilvl_el = num_pr.find(qn('w:ilvl'))
    if ilvl_el is not None:
        ilvl_el.set(qn('w:val'), str(int(ilvl) - 1))


def _heading4_conflict_message(heading3_text):
    """Error text for the Heading 4 / @@@STEPS@@@ ban. Steps sit on the
    heading list's level directly below Heading 3 - the same level
    Heading 4 uses - so both under one Heading 3 would share, and
    corrupt, one counter."""
    return (
        f'Heading 3 "{heading3_text}" contains both a #### (Heading 4) and a '
        "@@@STEPS@@@ block - steps share Heading 4's numbering level, so the two "
        'cannot be combined under one Heading 3. Move the Heading 4 content under '
        'its own ### heading, or make it plain text.'
    )


NO_HEADING3_MESSAGE = (
    '@@@STEPS@@@ block has no ### (Heading 3) above it in its section - steps are '
    'numbered <section>.<subsection>.<step>, so every @@@STEPS@@@ block must sit '
    'under a Heading 3. Add a ### heading above it.'
)


def apply_step_list_numbering(docx_file, clarification_abstract_num_id):
    """
    Walks docx_file's (Part D's) paragraphs in document order, tracking
    whether a @@@STEPS@@@ block is open and which Heading 3 is in scope.

    - Every ilvl-0 #.-list paragraph inside an open block becomes a
      'Dilon Step Heading' paragraph with its Pandoc list numbering
      stripped. It gets NO numbering here - link_steps_to_heading_numbering()
      attaches it to the heading list after the docxcompose merge.
    - Every ilvl>=1 #.-list paragraph (an ordered "clarification") is
      relettered onto a fresh numId of the 'Dilon Step Clarification List'
      abstract list, one fresh instance per top-level step.
    - A bullet-list paragraph keeps its bullet styling but has its ilvl
      decremented by one (see _decrement_bullet_ilvl()).

    Raises StepBlockError (compilation-halting) for:
    - an @@@STEPS@@@ with no matching @@@END_STEPS@@@, an @@@END_STEPS@@@
      with no block open, or a block reopened before closing;
    - a block left open across a Heading 1, 2, or 3;
    - a block with no Heading 3 above it since the last Heading 1 or 2;
    - a Heading 3 containing both a Heading 4 and a block, in either order.

    Returns the number of paragraphs converted (steps + clarifications).
    """
    from docx import Document
    doc = Document(docx_file)
    numbering_part = doc.part.numbering_part
    numbering_element = numbering_part.element if numbering_part is not None else None

    decimal_ids = _decimal_abstract_num_ids(numbering_element) if numbering_element is not None else set()
    num_id_to_abstract = _num_id_to_abstract_map(numbering_element) if numbering_element is not None else {}

    heading_style_available = 'Dilon Step Heading' in {s.name for s in doc.styles}
    if not heading_style_available:
        print("  Warning: template has no 'Dilon Step Heading' style; step numbering skipped")

    inside_steps = False
    marker_elements = []
    current_clarification_num_id = None
    numbered = 0

    # Per-Heading-3 scope, for the Heading 4 / no-Heading-3 rules. None
    # means "no Heading 3 seen yet in the current Heading 2".
    current_heading3_text = None
    heading3_has_steps = False
    heading3_has_heading4 = False

    for para in doc.paragraphs:
        stripped = para.text.strip()
        style_name = para.style.name if para.style is not None and para.style.name else ''

        # Heading 1 resets the scope too: it's off the heading list, so Word
        # wouldn't restart step counters there on its own.
        if style_name.startswith(('Heading 1', 'Heading 2', 'Heading 3')):
            if inside_steps:
                raise StepBlockError("@@@STEPS@@@ has no matching @@@END_STEPS@@@ before the next section heading")
            current_heading3_text = stripped if style_name.startswith('Heading 3') else None
            heading3_has_steps = False
            heading3_has_heading4 = False
            continue

        if style_name.startswith('Heading 4'):
            if heading3_has_steps:
                raise StepBlockError(_heading4_conflict_message(current_heading3_text))
            heading3_has_heading4 = True
            continue

        if stripped == '@@@STEPS@@@':
            if inside_steps:
                raise StepBlockError("@@@STEPS@@@ opened again before the previous block's @@@END_STEPS@@@")
            if current_heading3_text is None:
                raise StepBlockError(NO_HEADING3_MESSAGE)
            if heading3_has_heading4:
                raise StepBlockError(_heading4_conflict_message(current_heading3_text))
            inside_steps = True
            heading3_has_steps = True
            marker_elements.append(para._p)
            continue

        if stripped == '@@@END_STEPS@@@':
            if not inside_steps:
                raise StepBlockError("@@@END_STEPS@@@ found with no matching @@@STEPS@@@ open")
            inside_steps = False
            marker_elements.append(para._p)
            continue

        if not inside_steps:
            continue

        num_id, ilvl = _paragraph_num_id_and_ilvl(para._p)
        if num_id is None:
            continue  # non-list paragraph inside a block - left alone
        if num_id_to_abstract.get(num_id) not in decimal_ids:
            _decrement_bullet_ilvl(para._p, ilvl)  # bullet - left un-styled, but re-leveled
            continue

        if ilvl in (None, '0'):
            current_clarification_num_id = None
            if not heading_style_available:
                continue
            _strip_num_pr(para._p)
            para.style = doc.styles['Dilon Step Heading']
            numbered += 1
        else:
            if clarification_abstract_num_id is None:
                continue
            if current_clarification_num_id is None:
                current_clarification_num_id = create_num_instance(numbering_element, clarification_abstract_num_id)
            para.style = doc.styles['Dilon Step Clarification List']
            num_pr = para._p.find(qn('w:pPr')).find(qn('w:numPr'))
            num_pr.find(qn('w:numId')).set(qn('w:val'), str(current_clarification_num_id))
            ilvl_el = num_pr.find(qn('w:ilvl'))
            if ilvl_el is None:
                ilvl_el = OxmlElement('w:ilvl')
                num_pr.insert(0, ilvl_el)
            ilvl_el.set(qn('w:val'), '0')
            numbered += 1

    if inside_steps:
        raise StepBlockError("@@@STEPS@@@ has no matching @@@END_STEPS@@@ before the end of the document")

    for p_el in marker_elements:
        p_el.getparent().remove(p_el)

    if marker_elements or numbered:
        doc.save(docx_file)
        if numbered:
            print(f"  Converted {numbered} step/clarification paragraph(s)")
    return numbered


def link_steps_to_heading_numbering(docx_file):
    """
    Post-merge pass: attaches every 'Dilon Step Heading' paragraph in the
    FINAL assembled docx_file to the headings' own multilevel list, one
    level below Heading 3. The numId and Heading 3's ilvl are read from
    the document's 'Heading 3' style (never hard-coded), so the step's
    Word list label renders "<H2>.<H3>.<step>", restarts at each Heading
    3, and continues when a user presses Enter after a step in Word.

    Must run AFTER the docxcompose merge: Composer.add_numberings() remaps
    every paragraph-level numId in an appended part onto a fresh <w:num>
    backed by a *copy* of the abstractNum, so a step linked before the
    merge would land in a separate list whose Heading 2/3 counters never
    advance. Headings avoid the remap because their numbering comes from
    their style, which is why this reads the style.

    Returns the number of steps linked; 0 (with a printed warning) if the
    document's 'Heading 3' style carries no list numbering.
    """
    from docx import Document
    doc = Document(docx_file)

    try:
        heading3_p_pr = doc.styles['Heading 3'].element.pPr
    except KeyError:
        heading3_p_pr = None
    heading3_num_pr = heading3_p_pr.numPr if heading3_p_pr is not None else None
    if heading3_num_pr is None or heading3_num_pr.numId is None:
        print("  Warning: 'Heading 3' style has no list numbering; steps left unnumbered")
        return 0

    heading_num_id = heading3_num_pr.numId.val
    heading3_ilvl = heading3_num_pr.ilvl.val if heading3_num_pr.ilvl is not None else 0
    step_ilvl = heading3_ilvl + 1

    linked = 0
    for para in doc.paragraphs:
        if para.style is None or para.style.name != 'Dilon Step Heading':
            continue
        # get_or_add_numPr() inserts <w:numPr> in schema order within <w:pPr>.
        num_pr = para._p.get_or_add_pPr().get_or_add_numPr()
        num_pr.get_or_add_ilvl().val = step_ilvl
        num_pr.get_or_add_numId().val = heading_num_id
        linked += 1

    if linked:
        doc.save(docx_file)
        print(f"  Linked {linked} step(s) to the heading list numbering")
    return linked


def resolve_step_reference(para, bookmark_name):
    """
    type_resolvers['step'] callback for
    dilon_docx_common.resolve_reference_markers(): literal "Step " + a
    REF field with \\w (the bookmarked paragraph's list number in full
    context, e.g. "2.3.1") and \\h (hyperlink). A step's number is its
    native list label (see link_steps_to_heading_numbering()), so the
    bookmark only has to sit somewhere inside the step's paragraph - no
    narrowing needed. The in-place number carries no "Step " word, so it's
    added here, at the reference site.
    """
    para.add_run('Step ')
    add_complex_field(para, f'REF {bookmark_name} \\w \\h', '1')


