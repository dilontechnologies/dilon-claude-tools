# STEPS Native List Numbering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compiled `@@@STEPS@@@` items become real Word list items (numbered `2.3.1`, restarting at each Heading 3). Pressing Enter after a step in Word then adds the next numbered step.

**Architecture:**
- **Before merge:** `step_numbering.py` stops prepending `STYLEREF`/`SEQ` fields. It only restyles steps (`Dilon Step Heading`, with no numbering on the paragraph) and enforces two new compile errors:
  - a Heading 4 in the same Heading 3 as a steps block;
  - a steps block with no Heading 3 above it.
- **After merge:** a new pass, `link_steps_to_heading_numbering()`, runs on the final merged `.docx`. It attaches every step to the headings' own multilevel list, at Heading 3's level + 1.
  - Why after the merge: `docxcompose` remaps any list ID set directly on a paragraph into a copied, separate list. Doing this before the merge would break the "2.3" prefix.
- **Cross-references:** step references switch from `REF \h` on a narrowed bookmark to `REF \w \h`.

**Tech Stack:** Python 3.8+, python-docx, lxml, docxcompose, Pandoc. Tests are the repo's own direct-invocation `check()` suites (no pytest).

**Spec:** `docs/superpowers/specs/2026-09-25-steps-native-list-numbering-design.md`

## Execution Outcome (added after execution)

Executed inline 2026-09-25; all five tasks completed. The final whole-branch review found that Review Focus item 4's test (Task 4) used a paragraph shape Word never produces: Tab on a step actually restyles it Heading 5. That test was replaced with the real shape, the extractor was fixed to keep such steps in the procedure, the Task 5 styling-guide line about Tab was rewritten, and a Heading 1 scope reset was added to Task 1's rules. See the spec's corrected sections and the "fix: address final review" commit.

## Global Constraints

- Numbering: the list ID (`numId`) comes from the **final document's** `Heading 3` style definition, and the level (`ilvl`) is Heading 3's `ilvl` + 1. Never hard-code `68` or `2`.
- Steps carry **no** paragraph-level list numbering (`numPr`) before the merge. It is added only by `link_steps_to_heading_numbering()` after `composer.save()`, and only when `include_front_matter: true`.
- No template edits. `templates/TEMPLATE_Word_Base.docx` is not modified.
- Malformed input halts with `StepBlockError`. A missing style warns and degrades, the existing convention.
- Step cross-reference field: literal `"Step "` + `REF <bookmark> \w \h`.
- Heading 4 ban: a Heading 3 may contain a `@@@STEPS@@@` block or Heading 4s, not both, in either order. The state resets at every Heading 3 and Heading 2.
- Run tests with the repo's own runners:
  - `python tests/run_tests.py`
  - `python tests/run_form_tests.py`
  - `python tests/run_extractor_tests.py`
- Commits go on the current `DEV/...` branch and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Prerequisite (user):** the working tree has uncommitted, unrelated date-format edits in six files, including `skills/dilon-document-compiler/SKILL.md` and `skills/dilon-document-writer/MARKDOWN_STYLING_GUIDE.md`, which Task 5 also edits. Commit or stash them before Task 1 so this plan's commits don't pick them up.

## Review Focus

1. **Existing markdown with `@@@STEPS@@@` directly under a `##` (legacy authoring) now fails to compile.** The error must tell the author the fix: put the steps under a `###`. Test: Task 1 `test_apply_step_list_numbering_steps_without_heading3_raises`.
2. **`####` placed *inside* an open `@@@STEPS@@@` block** must raise the Heading 4 conflict error, not a confusing "unclosed block" error. Test: Task 1 `test_apply_step_list_numbering_heading4_inside_open_block_raises`.
3. **A step a user added in Word with Enter** (a `Dilon Step Heading` paragraph with native numbering and no typed number) must re-extract as a `#.` step. Test: Task 4 round-trip test.
4. **A step a user Tab-demoted in Word** (level 3) must not be dropped by the extractor. Test: Task 4 `test_build_markdown_body_dilon_step_heading_with_native_numbering_any_level`.
5. **A `{#step:x}` anchor on a step in the *second* steps block of a Heading 3** must still resolve after the merge. Test: Task 3 end-to-end fixture puts the anchor there.

## Running a single test

The suites have no per-test selector. To run one test function:

```bash
python -c "import sys; sys.path.insert(0, 'tests'); import run_tests as t; t.TEST_OUTPUT_DIR.mkdir(exist_ok=True); t.TEST_NAME(); sys.exit(1 if t.failed else 0)"
```

(For the extractor suite, swap `run_tests` for `run_extractor_tests`.) Exit code 1 means at least one `check()` printed `[FAIL]`.

---

### Task 1: Field-free step paragraphs + Heading 4 / no-Heading-3 bans

**Files:**
- Modify: `skills/dilon-document-compiler/scripts/step_numbering.py`
  - module docstring (lines 1-9)
  - imports (lines 20-28)
  - delete `_prepend_step_number_fields()` (193-230) and `_find_step_bookmark_start_in()` (251-260)
  - rewrite `apply_field_based_step_numbering()` (263-368) as `apply_step_list_numbering()`
- Modify: `skills/dilon-document-compiler/scripts/generate_dilon_doc.py:93-98` (import) and `:513` (call site)
- Test: `tests/run_tests.py`
  - rename/rewrite the `test_apply_field_based_step_numbering_*` tests (1953-2133) and their `main()` calls (3002-3010)

**Interfaces:**
- Produces: `step_numbering.apply_step_list_numbering(docx_file, clarification_abstract_num_id) -> int`. Same signature and return value (the count of paragraphs converted) as the function it replaces.
- Produces: `step_numbering.StepBlockError` (unchanged class) with two new messages:
  - no Heading 3: contains `"Heading 3"` and `"@@@STEPS@@@"`;
  - Heading 4 conflict: contains the Heading 3's text and `"Heading 4"`.

- [ ] **Step 1: Rename the existing tests' calls and rewrite the field-shape assertions**

In `tests/run_tests.py`:
- Replace every `step_numbering.apply_field_based_step_numbering(` with `step_numbering.apply_step_list_numbering(`.
- Rename each `def test_apply_field_based_step_numbering_<x>` to `def test_apply_step_list_numbering_<x>`, and update the matching calls in `main()`.

Leave `test_resolve_step_reference_builds_composite_field` and the end-to-end tests to Task 3 (only rename their call, if they have one).

Replace the field assertions at the end of `test_apply_step_list_numbering_single_step` (old lines 1979-1985) with:

```python
    for p in step_paras:
        num_id, _ = dilon_docx_common._paragraph_num_id_and_ilvl(p._p)
        check(num_id is None,
              "a step carries no paragraph-level numPr before the merge "
              "(link_steps_to_heading_numbering() adds it post-merge)")

    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    check('STYLEREF 3' not in xml and 'SEQ DilonStep' not in xml,
          "no STYLEREF/SEQ step-number fields are generated anymore")
```

Replace `test_apply_field_based_step_numbering_number_precedes_step_text` entirely with:

```python
def test_apply_step_list_numbering_step_text_is_untouched():
    """With native list numbering the number is Word's list label, not
    text in the paragraph - so the paragraph's text is exactly the
    author's step text, with no number or tab run prepended."""
    md = "## Major Section\n\n### Subsection Title\n\n@@@STEPS@@@\n\n#. Wear clean gloves.\n\n@@@END_STEPS@@@\n"
    docx_path = TEST_OUTPUT_DIR / "step_numbering_step_text_test.docx"
    compiler.markdown_to_docx(md, docx_path, reference_doc=SIGNATURE_TEMPLATE)

    clarification_id = step_numbering.get_step_clarification_abstract_num_id(SIGNATURE_TEMPLATE)
    step_numbering.apply_step_list_numbering(docx_path, clarification_id)

    doc = Document(docx_path)
    step_para = [p for p in doc.paragraphs if p.style and p.style.name == 'Dilon Step Heading'][0]
    check(step_para.text == 'Wear clean gloves.',
          f"step paragraph text is exactly the authored text (got {step_para.text!r})")
```

(Update its `main()` call to the new name.)

In `test_apply_step_list_numbering_unclosed_block_raises`, the fixture has no heading, so the new no-Heading-3 check would fire first. Change its `md` to:

```python
    md = "## Major Section\n\n### Subsection Title\n\n@@@STEPS@@@\n\n#. First\n"
```

- [ ] **Step 2: Add the new ban tests**

Add after `test_apply_step_list_numbering_preserves_inline_formatting`:

```python
def _expect_step_block_error(md, docx_name, expected_fragments, description):
    """Compiles md to Part D, runs apply_step_list_numbering(), and checks
    it raises StepBlockError whose message contains every fragment."""
    docx_path = TEST_OUTPUT_DIR / docx_name
    compiler.markdown_to_docx(md, docx_path, reference_doc=SIGNATURE_TEMPLATE)
    clarification_id = step_numbering.get_step_clarification_abstract_num_id(SIGNATURE_TEMPLATE)
    try:
        step_numbering.apply_step_list_numbering(docx_path, clarification_id)
        check(False, f"{description} raises StepBlockError")
    except step_numbering.StepBlockError as exc:
        message = str(exc)
        check(all(f in message for f in expected_fragments),
              f"{description}: error names {expected_fragments} (got: {message})")


def test_apply_step_list_numbering_heading4_before_steps_raises():
    _expect_step_block_error(
        "## Major Section\n\n### Assembly\n\n#### Tools\n\nA torque driver.\n\n"
        "@@@STEPS@@@\n\n#. First.\n\n@@@END_STEPS@@@\n",
        "step_numbering_h4_before_test.docx",
        ['Assembly', 'Heading 4'],
        "a Heading 4 followed by @@@STEPS@@@ under one Heading 3",
    )


def test_apply_step_list_numbering_heading4_after_steps_raises():
    _expect_step_block_error(
        "## Major Section\n\n### Assembly\n\n@@@STEPS@@@\n\n#. First.\n\n@@@END_STEPS@@@\n\n"
        "#### Notes\n\nSome notes.\n",
        "step_numbering_h4_after_test.docx",
        ['Assembly', 'Heading 4'],
        "@@@STEPS@@@ followed by a Heading 4 under one Heading 3",
    )


def test_apply_step_list_numbering_heading4_inside_open_block_raises():
    _expect_step_block_error(
        "## Major Section\n\n### Assembly\n\n@@@STEPS@@@\n\n#. First.\n\n"
        "#### Stray Sub-heading\n\n#. Second.\n\n@@@END_STEPS@@@\n",
        "step_numbering_h4_inside_test.docx",
        ['Assembly', 'Heading 4'],
        "a Heading 4 inside an open @@@STEPS@@@ block",
    )


def test_apply_step_list_numbering_steps_without_heading3_raises():
    _expect_step_block_error(
        "## Major Section\n\n@@@STEPS@@@\n\n#. First.\n\n@@@END_STEPS@@@\n",
        "step_numbering_no_h3_test.docx",
        ['Heading 3', '@@@STEPS@@@'],
        "a @@@STEPS@@@ block with no Heading 3 above it",
    )


def test_apply_step_list_numbering_heading4_in_different_heading3_allowed():
    """The ban is per Heading 3: a Heading 4 under one Heading 3 and steps
    under a different Heading 3 (even in the same Heading 2) are fine."""
    md = (
        "## Major Section\n\n### Background\n\n#### Tools\n\nA torque driver.\n\n"
        "### Procedure\n\n@@@STEPS@@@\n\n#. First.\n\n@@@END_STEPS@@@\n"
    )
    docx_path = TEST_OUTPUT_DIR / "step_numbering_h4_other_h3_test.docx"
    compiler.markdown_to_docx(md, docx_path, reference_doc=SIGNATURE_TEMPLATE)
    clarification_id = step_numbering.get_step_clarification_abstract_num_id(SIGNATURE_TEMPLATE)
    try:
        count = step_numbering.apply_step_list_numbering(docx_path, clarification_id)
        check(count == 1, f"the step under the other Heading 3 is converted (got {count})")
    except step_numbering.StepBlockError as exc:
        check(False, f"a Heading 4 in a different Heading 3 must not raise (got: {exc})")
```

Add all five calls to `main()`, right after `test_apply_step_list_numbering_preserves_inline_formatting()`.

- [ ] **Step 3: Run the step tests and confirm they fail**

Run: `python tests/run_tests.py 2>&1 | grep -E "FAIL|Error|AttributeError" | head -30`

Expected: the run crashes with `AttributeError: module 'step_numbering' has no attribute 'apply_step_list_numbering'` (the tests now call the new name). Record the output as the failing evidence.

- [ ] **Step 4: Implement `apply_step_list_numbering()`**

In `step_numbering.py`:
- **Module docstring:** replace lines 1-9 with:

```python
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
(gitignored; see git history of this file for the rationale if absent).
"""
```

- **Imports:** replace lines 20-28 with (dropping `add_field_simple_run` and `_narrow_bookmark`, which are no longer used here):

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from dilon_docx_common import (
    add_complex_field,
    _decimal_abstract_num_ids,
    _num_id_to_abstract_map,
    _paragraph_num_id_and_ilvl,
)
```

- **Delete** `_prepend_step_number_fields()` and `_find_step_bookmark_start_in()`.

- **Update** `_strip_num_pr()`'s docstring: "restyling it 'Dilon Step Heading'" becomes "restyling it 'Dilon Step Heading' (the list link is re-added post-merge by link_steps_to_heading_numbering())".

- **Add** above the main function:

```python
def _heading4_conflict_message(heading3_text):
    """Error text for the Heading 4 / @@@STEPS@@@ ban. Steps sit on the
    heading list's level directly below Heading 3 - the same level
    Heading 4 uses - so both under one Heading 3 would share, and
    corrupt, one counter."""
    return (
        f'Heading 3 "{heading3_text}" contains both a #### (Heading 4) and a '
        '@@@STEPS@@@ block - steps share Heading 4\'s numbering level, so the two '
        'cannot be combined under one Heading 3. Move the Heading 4 content under '
        'its own ### heading, or make it plain text.'
    )


NO_HEADING3_MESSAGE = (
    '@@@STEPS@@@ block has no ### (Heading 3) above it in its section - steps are '
    'numbered <section>.<subsection>.<step>, so every @@@STEPS@@@ block must sit '
    'under a Heading 3. Add a ### heading above it.'
)
```

- **Replace** `apply_field_based_step_numbering()` with:

```python
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
    - a block left open across a Heading 2 or Heading 3;
    - a block with no Heading 3 above it in its Heading 2;
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

        if style_name.startswith('Heading 2') or style_name.startswith('Heading 3'):
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
```

- **Update the `StepBlockError` docstring**: replace its "Unlike the old markdown-level version... apply_section_scoped_step_numbering()" sentences with "Raised post-conversion by apply_step_list_numbering(); see its docstring for the full list of conditions."
- **Fix `ensure_blank_line_around_steps_markers()`'s docstring**: it references `apply_section_scoped_step_numbering()`; change it to `apply_step_list_numbering()`.

In `generate_dilon_doc.py`:
- Change the import at line 96 from `apply_field_based_step_numbering,` to `apply_step_list_numbering,`.
- At line 513, change the call to `apply_step_list_numbering(temp_part_d, step_clarification_abstract_num_id)`.
- Change the log line above it to `print("Converting @@@STEPS@@@ blocks...")`.

- [ ] **Step 5: Run the step tests and confirm they pass**

Run: `python tests/run_tests.py 2>&1 | grep -E "step_list_numbering|StepBlockError|FAIL" | head -40`

Expected: every `apply_step_list_numbering` check passes. The existing `test_resolve_step_reference_builds_composite_field` (bookmark-narrowing check) and the end-to-end tests asserting `STYLEREF 3 \s` / `REF ... \h` are **expected to FAIL** until Task 3. The `FULL_XREF_MARKDOWN` compile is expected to fail on the new no-Heading-3 error. Confirm no other failures.

- [ ] **Step 6: Commit**

```bash
git add skills/dilon-document-compiler/scripts/step_numbering.py skills/dilon-document-compiler/scripts/generate_dilon_doc.py tests/run_tests.py
git commit -m "feat: compile @@@STEPS@@@ steps without number fields, ban Heading 4 alongside steps

Steps become plain 'Dilon Step Heading' paragraphs ahead of the move to
native list numbering (linked post-merge in a follow-up commit). Adds
StepBlockError for a Heading 4 sharing a Heading 3 with a steps block
(steps will share Heading 4's list level) and for a steps block with
no Heading 3 above it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Post-merge link to the heading list

**Files:**
- Modify: `skills/dilon-document-compiler/scripts/step_numbering.py` (add `link_steps_to_heading_numbering()` after `apply_step_list_numbering()`)
- Modify: `skills/dilon-document-compiler/scripts/generate_dilon_doc.py:93-98` (import) and `:557` (after `composer.save(output_path)`)
- Test: `tests/run_tests.py`
  - new unit test;
  - `STEP_REDESIGN_MARKDOWN` (2162-2176);
  - `test_compile_field_based_step_numbering_end_to_end` (2179-2210), renamed `test_compile_step_list_numbering_end_to_end`.

**Interfaces:**
- Consumes: `apply_step_list_numbering()` from Task 1. Steps are `Dilon Step Heading` paragraphs with no `numPr`.
- Produces: `step_numbering.link_steps_to_heading_numbering(docx_file) -> int`. It returns the count of step paragraphs linked; 0 (with a warning) if `Heading 3` has no `numPr`.

- [ ] **Step 1: Write the failing unit test**

Add after the Task 1 ban tests:

```python
def _heading3_list_position(doc):
    """(numId, ilvl) as strings that a step should carry: the Heading 3
    style's own numId, one level below Heading 3's ilvl."""
    h3_num_pr = doc.styles['Heading 3'].element.pPr.numPr
    h3_ilvl = h3_num_pr.ilvl.val if h3_num_pr.ilvl is not None else 0
    return str(h3_num_pr.numId.val), str(h3_ilvl + 1)


def test_link_steps_to_heading_numbering_uses_heading3_list():
    md = "## Major Section\n\n### Subsection Title\n\n@@@STEPS@@@\n\n#. First.\n#. Second.\n\n@@@END_STEPS@@@\n"
    docx_path = TEST_OUTPUT_DIR / "step_link_unit_test.docx"
    compiler.markdown_to_docx(md, docx_path, reference_doc=SIGNATURE_TEMPLATE)
    clarification_id = step_numbering.get_step_clarification_abstract_num_id(SIGNATURE_TEMPLATE)
    step_numbering.apply_step_list_numbering(docx_path, clarification_id)

    linked = step_numbering.link_steps_to_heading_numbering(docx_path)
    check(linked == 2, f"both steps are linked (got {linked})")

    doc = Document(docx_path)
    expected = _heading3_list_position(doc)
    steps = [p for p in doc.paragraphs if p.style and p.style.name == 'Dilon Step Heading']
    positions = {dilon_docx_common._paragraph_num_id_and_ilvl(p._p) for p in steps}
    check(positions == {expected},
          f"every step sits on Heading 3's list, one level below it (expected {expected}, got {positions})")
```

Add `test_link_steps_to_heading_numbering_uses_heading3_list()` to `main()` after the Task 1 tests.

- [ ] **Step 2: Rewrite the end-to-end fixture and test**

Replace `STEP_REDESIGN_MARKDOWN` with a version that adds a second Heading 3 and moves the anchor onto a step in the **second** block (Review Focus 5):

```python
STEP_REDESIGN_MARKDOWN = (
    '\n## Carrier Board Assembly\n\n'
    '### Cleaning Procedure\n\n'
    '@@@STEPS@@@\n\n'
    '#. Wear clean gloves.\n'
    '#. Hold the board by the edges.\n'
    '    #. Simple dirt such as lint or light dust can be blown away before wiping.\n\n'
    '@@@END_STEPS@@@\n\n'
    'NOTE: Clean the entire crystal but give special attention to the polished end.\n\n'
    '@@@STEPS@@@\n\n'
    '#. Visually inspect both the crystal and the photomultiplier for defects. []{#step:inspect-crystal}\n'
    '#. Set the cleaned crystals aside on a clean lint free cloth.\n\n'
    '@@@END_STEPS@@@\n\n'
    '### Inspection Procedure\n\n'
    '@@@STEPS@@@\n\n'
    '#. Check the board under magnification.\n\n'
    '@@@END_STEPS@@@\n\n'
    'As described in [](#step:inspect-crystal), inspect before setting aside.\n'
)
```

Replace `test_compile_field_based_step_numbering_end_to_end` with:

```python
def test_compile_step_list_numbering_end_to_end():
    """Integration test through the real pipeline, including the
    docxcompose merge: two @@@STEPS@@@ blocks in one Heading 3 (split by a
    NOTE), a third block under a second Heading 3, a clarification, and a
    cross-reference. Every step in the FINAL document must sit on the
    Heading 3 style's own list (not a docxcompose-remapped copy), one level
    below Heading 3."""
    markdown = SAMPLE_MARKDOWN + STEP_REDESIGN_MARKDOWN
    input_md = TEST_OUTPUT_DIR / "compile_test_step_list_numbering.md"
    output_docx = TEST_OUTPUT_DIR / "compile_test_step_list_numbering.docx"
    input_md.write_text(markdown, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(COMPILER_SCRIPT), str(input_md), str(output_docx), str(SIGNATURE_TEMPLATE)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    check(result.returncode == 0, "compiler exits 0 for a document with @@@STEPS@@@ blocks")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return

    doc = Document(output_docx)
    check(all('@@@STEPS' not in p.text and '@@@END_STEPS' not in p.text for p in doc.paragraphs),
          "no wrapper marker text remains anywhere")
    step_paragraphs = [p for p in doc.paragraphs if p.style and p.style.name == 'Dilon Step Heading']
    check(len(step_paragraphs) == 5, f"all 5 top-level steps across three blocks get 'Dilon Step Heading' (got {len(step_paragraphs)})")
    clarification_paragraphs = [p for p in doc.paragraphs if p.style and p.style.name == 'Dilon Step Clarification List']
    check(len(clarification_paragraphs) == 1, f"the one nested clarification gets 'Dilon Step Clarification List' (got {len(clarification_paragraphs)})")

    expected = _heading3_list_position(doc)
    positions = {dilon_docx_common._paragraph_num_id_and_ilvl(p._p) for p in step_paragraphs}
    check(positions == {expected},
          f"every step in the merged document is on Heading 3's own list, one level down "
          f"(expected {expected}, got {positions})")

    with zipfile.ZipFile(output_docx) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    check('STYLEREF 3' not in xml and 'SEQ DilonStep' not in xml, "no field-based step numbers remain")
    check('w:name="step:inspect-crystal"' in xml, "the step's anchor survives as a real bookmark")
```

(The `REF ... \w \h` assertion is added in Task 3.) In `main()`, rename the call to `test_compile_step_list_numbering_end_to_end()`.

- [ ] **Step 3: Run both tests and confirm they fail**

Run:
```bash
python -c "import sys; sys.path.insert(0, 'tests'); import run_tests as t; t.TEST_OUTPUT_DIR.mkdir(exist_ok=True); t.test_link_steps_to_heading_numbering_uses_heading3_list(); t.test_compile_step_list_numbering_end_to_end(); sys.exit(1 if t.failed else 0)"
```
Expected:
- The unit test raises `AttributeError: ... no attribute 'link_steps_to_heading_numbering'`.
- Once the unit test is commented out, the end-to-end test prints `[FAIL] every step in the merged document is on Heading 3's own list ... got {(None, None)}`.

- [ ] **Step 4: Implement the post-merge pass**

Add to `step_numbering.py` after `apply_step_list_numbering()`:

```python
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
```

In `generate_dilon_doc.py`, add `link_steps_to_heading_numbering,` to the `from step_numbering import (...)` block. Then change:

```python
    composer.save(output_path)
```

to:

```python
    composer.save(output_path)

    # Steps are attached to the heading list only now, after the merge -
    # docxcompose would otherwise remap their numId onto a separate copy
    # of the list (see link_steps_to_heading_numbering()). Forms have no
    # @@@STEPS@@@ processing, so this runs in document mode only.
    if include_front_matter:
        print("Linking steps to heading numbering...")
        link_steps_to_heading_numbering(output_path)
```

- [ ] **Step 5: Run both tests and confirm they pass**

Run the Step 3 command. Expected: exit 0, all `[PASS]`.

- [ ] **Step 6: Commit**

```bash
git add skills/dilon-document-compiler/scripts/step_numbering.py skills/dilon-document-compiler/scripts/generate_dilon_doc.py tests/run_tests.py
git commit -m "feat: link @@@STEPS@@@ steps to the heading list as native Word list items

Runs after the docxcompose merge, since Composer.add_numberings() remaps
paragraph-level numIds onto a copied list and would detach steps from
the Heading 2/3 counters. Steps now number <H2>.<H3>.<step> natively,
restart at each Heading 3, and continue on Enter in Word.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Step cross-references via `REF \w`

**Files:**
- Modify: `skills/dilon-document-compiler/scripts/step_numbering.py`, `resolve_step_reference()` (old lines 371-384)
- Modify: `lib/dilon_docx_common.py:888-903` (comment only)
- Modify: `lib/dilon_docx_common.py:691` (stale `apply_step_numbering()` mention in a docstring)
- Test: `tests/run_tests.py`
  - `test_resolve_step_reference_builds_composite_field` (2135-2159)
  - `test_compile_step_list_numbering_end_to_end` (from Task 2)
  - `FULL_XREF_MARKDOWN` (2263-2270)
  - `test_compile_full_cross_reference_set_end_to_end` (2300)

**Interfaces:**
- Consumes: steps with their Pandoc-placed `step:` bookmark left where Pandoc put it (Task 1 no longer narrows it).
- Produces: `resolve_step_reference(para, bookmark_name)` appends a `"Step "` run + a `REF <bookmark_name> \w \h` complex field.

- [ ] **Step 1: Rewrite the reference tests**

Replace the body of `test_resolve_step_reference_builds_composite_field` after the `resolve_reference_markers(...)` call (old lines 2145-2159) with:

```python
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    check('REF step:x \\w \\h' in xml,
          "the reference is a full-context paragraph-number REF (\\w) - the step's number is its native list label")
    check('Step ' in xml, "the literal 'Step ' prefix is present at the reference site")

    doc = Document(docx_path)
    step_para = [p for p in doc.paragraphs if p.style and p.style.name == 'Dilon Step Heading'][0]
    check(any(el.get(qn('w:name')) == 'step:x' for el in step_para._p.iter(qn('w:bookmarkStart'))),
          "the step:x bookmark sits inside the step's own paragraph, which is all REF \\w needs")
```

Append to `test_compile_step_list_numbering_end_to_end`:

```python
    check('REF step:inspect-crystal \\w \\h' in xml,
          "a reference to a step in the second block of a Heading 3 resolves to a live REF \\w field")
```

Replace `FULL_XREF_MARKDOWN` so its steps block sits under a Heading 3 (the new rule):

```python
FULL_XREF_MARKDOWN = (
    '\n## Assembly Section {#sec:assembly}\n\n'
    '![A widget.](diagrams/example.png){#fig:widget}\n\n'
    '### Installation\n\n'
    '@@@STEPS@@@\n\n'
    '#. Install the widget. []{#step:install-widget}\n\n'
    '@@@END_STEPS@@@\n\n'
    'See [](#fig:widget), [](#sec:assembly), and [](#step:install-widget) for full context.\n'
)
```

In `test_compile_full_cross_reference_set_end_to_end`, change the step check to:

```python
    check('REF step:install-widget \\w \\h' in xml, "the step reference resolved")
```

Rename `test_resolve_step_reference_builds_composite_field` to `test_resolve_step_reference_uses_paragraph_number_field` (definition and `main()` call).

- [ ] **Step 2: Run the three tests and confirm they fail**

Run:
```bash
python -c "import sys; sys.path.insert(0, 'tests'); import run_tests as t; t.TEST_OUTPUT_DIR.mkdir(exist_ok=True); t.test_resolve_step_reference_uses_paragraph_number_field(); t.test_compile_step_list_numbering_end_to_end(); t.test_compile_full_cross_reference_set_end_to_end(); sys.exit(1 if t.failed else 0)"
```
Expected: `[FAIL]` on each `\w \h` check (the resolver still emits `REF ... \h`).

- [ ] **Step 3: Implement**

Replace `resolve_step_reference()` in `step_numbering.py` with:

```python
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
```

In `lib/dilon_docx_common.py`, replace the comment block at lines 888-903 with the version below. The code under it stays as is: figure captions still carry `fldSimple` number fields.

```python
        # A paragraph can open with <w:fldSimple> number fields - today a
        # figure caption's "Figure " + STYLEREF + "." + SEQ span (from
        # apply_figure_captions()); before 2026-09 also every @@@STEPS@@@
        # step. python-docx's para.text/para.runs only see plain <w:r>
        # children and silently skip <w:fldSimple>, so including the
        # literal runs interleaved between those fields in the rebuild
        # below once corrupted numbers like "6.5.7" into "6.57.".
        # Treating everything up to and including the last <w:fldSimple>
        # (plus any trailing bookmark markers) as an untouchable header
        # keeps that span exactly as it was built.
```

At line 691, replace `step_numbering.py's apply_step_numbering()` with `step_numbering.py's create_num_instance()`. First check the surrounding sentence (`sed -n 685,695p lib/dilon_docx_common.py`) and adjust the wording so it still reads correctly. The mechanism it describes is a fresh numId per list instance, which is exactly what `create_num_instance()` does.

- [ ] **Step 4: Run the three tests and confirm they pass**

Run the Step 2 command. Expected: exit 0.

- [ ] **Step 5: Run the full compiler suite**

Run: `python tests/run_tests.py 2>&1 | tail -5`
Expected: `N passed, 0 failed` and `All tests passed!`. Any failure here is a regression from Tasks 1-3; fix it before committing.

- [ ] **Step 6: Commit**

```bash
git add skills/dilon-document-compiler/scripts/step_numbering.py lib/dilon_docx_common.py tests/run_tests.py
git commit -m "feat: resolve step cross-references with REF \\w against native list numbers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Extractor handles natively numbered steps

**Files:**
- Modify: `skills/dilon-document-extractor/scripts/extract_docx.py:66-83` (comment), `:973-977` (summary warning wording)
- Test: `tests/run_extractor_tests.py` (two new tests + `main()` calls after `test_build_markdown_body_dilon_step_heading_warns_once_with_count()`, line 1619)

**Interfaces:**
- Consumes: the compiler's output from Tasks 1-3 (`Dilon Step Heading` + native `numPr`, no typed number).
- Produces: no API change.

> Note: `build_markdown_body()` already checks `is_dilon_step_heading()` *before* `paragraph_is_list_item()`, so these tests are expected to pass on first run. They are regression guards, not red-green tests. If either fails at Step 2, that is a real bug: fix it in `build_markdown_body()` before continuing.

- [ ] **Step 1: Write the tests**

Add after `test_build_markdown_body_dilon_step_heading_warns_once_with_count`:

```python
def test_build_markdown_body_dilon_step_heading_with_native_numbering_any_level():
    """Steps compiled since 2026-09 are 'Dilon Step Heading' paragraphs
    carrying native list numbering (numPr) and no typed number - including
    ones a user added in Word by pressing Enter, or demoted with Tab (a
    deeper ilvl). All must extract as #. steps inside @@@STEPS@@@, never
    as plain '-' list items and never dropped."""
    import extract_docx as ex
    from docx.oxml import OxmlElement
    doc = Document()
    doc.styles.add_style("Dilon Step Heading", WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("Mixing Epoxy", style="Heading 3")
    for text, ilvl in [("Blend the two components.", "2"), ("Added in Word with Enter.", "2"), ("Demoted with Tab.", "3")]:
        para = doc.add_paragraph(text, style="Dilon Step Heading")
        num_pr = OxmlElement("w:numPr")
        ilvl_el = OxmlElement("w:ilvl")
        ilvl_el.set(qn("w:val"), ilvl)
        num_id_el = OxmlElement("w:numId")
        num_id_el.set(qn("w:val"), "1")
        num_pr.append(ilvl_el)
        num_pr.append(num_id_el)
        para._p.get_or_add_pPr().append(num_pr)

    blocks = list(ex.iter_block_items(doc))
    body, warnings = ex.build_markdown_body(doc, blocks, 1, TEST_OUTPUT_DIR, {"revisions": []})

    check(body.count("@@@STEPS@@@") == 1, "natively numbered steps form one @@@STEPS@@@ block")
    for text in ["Blend the two components.", "Added in Word with Enter.", "Demoted with Tab."]:
        check(f"#. {text}" in body, f"step {text!r} extracted as a #. item")
    check("- Blend" not in body, "a natively numbered step is not mistaken for a plain list item")


def test_extract_round_trip_of_compiled_steps():
    """Compile a steps document with the real compiler, then extract it:
    the steps come back as a @@@STEPS@@@ block with clean text."""
    import extract_docx as ex
    compiler_script = REPO_ROOT / "skills" / "dilon-document-compiler" / "scripts" / "generate_dilon_doc.py"
    base_template = REPO_ROOT / "templates" / "TEMPLATE_Word_Base.docx"
    TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_md = TEST_OUTPUT_DIR / "round_trip_steps.md"
    compiled = TEST_OUTPUT_DIR / "round_trip_steps.docx"
    source_md.write_text(
        '---\ntitle: "Round Trip"\nauthor: "Test"\ndepartment: "Eng"\ndoc_number: "WI-99999"\n'
        'current_revision: "00"\ndepartment_head: "Head"\nsignature_fields: []\n'
        'revisions:\n  - number: "00"\n    description: "Initial"\n    eco_number: "ECO-0"\n    eco_date: "01-01-2026"\n'
        '---\n\n## Assembly\n\n### Cleaning Procedure\n\n@@@STEPS@@@\n\n'
        '#. Wear clean gloves.\n#. Hold the board by the edges.\n\n@@@END_STEPS@@@\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(compiler_script), str(source_md), str(compiled), str(base_template)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    check(result.returncode == 0, "round-trip source compiles")
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        return

    out = ex.extract(compiled, TEST_OUTPUT_DIR / "round_trip_steps_extracted")
    body = Path(out["markdown_path"]).read_text(encoding="utf-8")
    check("@@@STEPS@@@" in body and "@@@END_STEPS@@@" in body, "compiled steps re-extract inside a @@@STEPS@@@ block")
    check("#. Wear clean gloves." in body and "#. Hold the board by the edges." in body,
          "each step re-extracts as a clean #. item with no stray number text")
```

Add both calls to `main()` after `test_build_markdown_body_dilon_step_heading_warns_once_with_count()`.

If `signature_fields: []` fails to compile, check what `run_tests.py`'s `SAMPLE_MARKDOWN` uses and copy its front matter instead. Don't change the compiler to accept it.

- [ ] **Step 2: Run the extractor suite**

Run: `python tests/run_extractor_tests.py 2>&1 | tail -5`
Expected: `0 failed`. If a new test fails, fix `build_markdown_body()` so that `is_dilon_step_heading()` wins over list detection, then re-run.

- [ ] **Step 3: Update the extractor comment and warning**

Replace the comment block at `extract_docx.py:66-83` (keep the `STALE_STEP_NUMBER_RE` line below it) with:

```python
# 'Dilon Step Heading' is this compiler's own paragraph style for
# @@@STEPS@@@ items, so a source document using it was compiled by this
# same pipeline at some point. Two generations exist:
#
# - Since 2026-09 (step_numbering.py's link_steps_to_heading_numbering()):
#   the step is a native Word list item on the heading list. Its number is
#   Word's list label, not paragraph text, so .text is just the step text.
#   Steps a user added in Word (Enter) or demoted (Tab) look the same.
# - Before 2026-09: the number was a live 'STYLEREF 3 \\s' + '.' +
#   'SEQ DilonStep \\* ARABIC \\s 3' field pair ahead of the text.
#   python-docx's .text reads a field's last-cached display result, which
#   can be stale: real WI-00077 caches "1.1" on all 77 steps, and real
#   WI-00088's STYLEREF cached blank, so its steps read bare ".". The
#   pattern below accepts digits/dots/nothing before the tab so both
#   shapes strip cleanly; it is a no-op on the newer generation.
```

Change the summary warning at lines 973-977 to:

```python
        warnings.append(
            f"{dilon_step_heading_count} '{DILON_STEP_HEADING_STYLE}'-styled paragraph(s) "
            "converted to @@@STEPS@@@ items (stale field-based step numbers from pre-2026-09 "
            "compiles stripped, if present) - spot-check a sample for correctness"
        )
```

- [ ] **Step 4: Re-run the extractor suite**

Run: `python tests/run_extractor_tests.py 2>&1 | tail -5`
Expected: `0 failed`. The existing warning test checks only for `"Dilon Step Heading"` and the count, both kept.

- [ ] **Step 5: Commit**

```bash
git add skills/dilon-document-extractor/scripts/extract_docx.py tests/run_extractor_tests.py
git commit -m "test: extractor round-trips natively numbered @@@STEPS@@@ steps

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Docs, changelog, full verification, manual Word check

**Files:**
- Modify: `skills/dilon-document-writer/MARKDOWN_STYLING_GUIDE.md:439-455` (Section 6 rules + anchor paragraph)
- Modify: `skills/dilon-document-compiler/SKILL.md:41`
- Modify: `CHANGELOG.md` (new `[Unreleased]` section above `[2.0.3]`)
- Modify: `CLAUDE.md` (Skill 2 capabilities + "Document Generation" bullets): add one line about steps.

- [ ] **Step 1: Styling guide**

In Section 6's **Rules** list, replace the bullet at line 441 with:

```markdown
- A step's number is scoped to the nearest preceding `###` (Heading 3) - a new `###` always starts a fresh count at 1. Every `@@@STEPS@@@` block within the *same* Heading 3 subsection shares one continuous count automatically - no marker needed to "continue" a procedure interrupted by prose, a photo, or a `NOTE:`.
- Every `@@@STEPS@@@` block must sit under a `###` (Heading 3). A block directly under a `##` fails compilation with an error.
- A `###` subsection that contains `@@@STEPS@@@` cannot also contain a `####` (Heading 4), before or after the steps - steps use Heading 4's numbering level, so the two would share one counter. Compilation fails with an error naming the subsection; move the `####` content under its own `###`, or make it plain text.
- In the compiled Word document, steps are real Word numbered-list items: pressing Enter after a step adds the next numbered step, and inserting or deleting steps renumbers the rest automatically. Pressing Tab on a step demotes it to a four-level number (e.g. `2.3.1.1`).
```

Replace the paragraph at line 455 with:

```markdown
The anchor must sit on a **top-level step**, not on a nested clarification - a clarification keeps its own lettering (`a.`, `b.`) and isn't currently a valid reference target.
```

- [ ] **Step 2: Compiler SKILL.md**

Replace line 41 with:

```markdown
- A malformed `@@@STEPS@@@`/`@@@END_STEPS@@@` pairing (unclosed or nested), a `@@@STEPS@@@` block with no `###` (Heading 3) above it, or a `###` subsection containing both a `####` (Heading 4) and a `@@@STEPS@@@` block
```

- [ ] **Step 3: CHANGELOG**

Insert above `## [2.0.3] - 2026-09-01`:

```markdown
## [Unreleased]

### Changed
- `dilon-document-compiler`: `@@@STEPS@@@` steps are now native Word numbered-list items on the heading list instead of `STYLEREF`/`SEQ` fields - pressing Enter after a step in Word adds the next numbered step, and numbers never go stale. Step cross-references now use `REF \w`.
- **BREAKING:** a `@@@STEPS@@@` block must sit under a `###` (Heading 3), and a Heading 3 containing steps cannot also contain a `####` (Heading 4); both now fail compilation with an error. Documents authored with steps directly under a `##` need a `###` added.

### Fixed
- `dilon-document-extractor`: covered natively numbered steps (including ones added in Word) with round-trip tests
```

- [ ] **Step 4: CLAUDE.md**

In the "Document Generation (Word Compilation)" bullet list, add after the "Image aspect ratio lock" bullet:

```markdown
- **Procedure steps**: `@@@STEPS@@@` items compile to native Word list items on the headings' own multilevel list, one level below Heading 3 (`step_numbering.py`). The list link is added by `link_steps_to_heading_numbering()` on the *final merged* document, because docxcompose remaps paragraph-level numIds into a copied list during the merge. Consequence: a Heading 3 can't contain both Heading 4s and steps, and steps must sit under a Heading 3 (`StepBlockError`).
```

- [ ] **Step 5: Run all three suites**

Run:
```bash
python tests/run_tests.py 2>&1 | tail -3; python tests/run_form_tests.py 2>&1 | tail -3; python tests/run_extractor_tests.py 2>&1 | tail -3
```
Expected: each reports `0 failed`. Paste the three tails into the task report.

- [ ] **Step 6: Build the manual-test document**

Run:
```bash
python skills/dilon-document-compiler/scripts/generate_dilon_doc.py tests/STYLING_TEST_TEMPLATE.md tests/test-output/MANUAL_STEPS_CHECK.docx templates/TEMPLATE_Word_Base.docx
```
Expected: exit 0 and the file exists. If `STYLING_TEST_TEMPLATE.md` now hits a new `StepBlockError`, fix the template's markdown (not the compiler) and note it in the commit.

- [ ] **Step 7: Commit**

```bash
git add skills/dilon-document-writer/MARKDOWN_STYLING_GUIDE.md skills/dilon-document-compiler/SKILL.md CHANGELOG.md CLAUDE.md
git commit -m "docs: document native-list @@@STEPS@@@ numbering and its heading rules

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Hand off the manual Word check to the user**

Ask the user to open `tests/test-output/MANUAL_STEPS_CHECK.docx` in Word and confirm:
- steps read `N.M.K` and restart at each Heading 3;
- Enter after a step creates the next numbered step, and later steps renumber;
- Enter on an empty step ends the list;
- after Ctrl+A, F9, step cross-references read `Step N.M.K`. If they don't, the fallback is `\r` in `resolve_step_reference()`;
- the step indent and tab layout matches the previous output. Watch for step text starting at different positions: the style's 0.25" tab stop is a pre-existing quirk, to be fixed separately if seen.

Do not mark the plan complete until the user reports back.

- [ ] **Step 9: Cleanup (after the user confirms and the work is merged)**

Per the user's global instructions: `docs/superpowers/` is gitignored in this repo, so nothing needs deleting from git. Delete the local spec and plan files once the work is merged.
