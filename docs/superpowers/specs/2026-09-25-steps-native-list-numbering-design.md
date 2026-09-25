# STEPS Numbering as Native Word List Items - Design

**Date:** 2026-09-25
**Status:** Approved in conversation, pending spec review
**Supersedes:** the field-based STEPS numbering introduced in commit `9a9dfbf` (2026-08-24)

## 1. Problem

`@@@STEPS@@@` items are compiled into `Dilon Step Heading` paragraphs whose
visible number ("2.3.1") is built from a `STYLEREF 3 \s` field, a literal
`.` run, and a `SEQ DilonStep \* ARABIC \s 3` field, followed by a tab run
(`step_numbering.py`'s `_prepend_step_number_fields()`).

Because the number is field codes rather than list numbering, a person
editing the compiled document in Word cannot add a step: pressing Enter
after a step creates a new paragraph carrying the style but no fields, so
it has no number. Fields also go stale - real WI-00077 archived with all 77
steps caching "1.1" because nothing refreshed them.

## 2. Goal

Compiled steps behave as a real Word numbered list:

- Pressing Enter after a step produces the next numbered step.
- Inserting or deleting a step renumbers the rest without an F9 refresh.
- The number format stays `<Heading 2>.<Heading 3>.<step>` ("2.3.1") and
  restarts at every Heading 3.
- `[](#step:label)` cross-references keep rendering "Step 2.3.1".

## 3. Key Constraint and Decision

The base template's headings are already native multilevel list numbering:
`Heading 2`, `Heading 3`, and `Heading 4` are levels 0, 1, 2 of `numId 68`
(`abstractNum 14`), formatted `%1`, `%1.%2`, `%1.%2.%3`. The only way to get
the live "2.3" prefix in a native list number is for steps to be members of
that same list, at level 2 - the level Heading 4 already occupies.

Steps and Heading 4s under the same Heading 3 would therefore share one
counter and corrupt each other's numbers. **Decision (user, 2026-09-25):**
ban the combination for now. A Heading 3 may contain a `@@@STEPS@@@` block
or Heading 4s, not both. Lifting the ban later would require a different
numbering design.

## 4. Design

### 4.1 Step paragraphs (`apply_field_based_step_numbering()`, to be renamed `apply_step_list_numbering()`)

For every top-level (ilvl 0, decimal) list paragraph inside an open
`@@@STEPS@@@` block:

1. Strip Pandoc's own `<w:numPr>` (unchanged).
2. Apply the `Dilon Step Heading` style (unchanged).
3. **Leave the step with no `numPr` at all in Part D.** The list link is
   added after merging (step 3a below), not here - see "Why post-merge".

3a. **Post-merge pass (`link_steps_to_heading_numbering()`)**, run on the
   final merged `.docx` right after `composer.save(output_path)`, in
   `include_front_matter: true` mode only: add direct paragraph numbering
   `<w:numPr><w:ilvl w:val="L+1"/><w:numId w:val="N"/></w:numPr>` to every
   `Dilon Step Heading` paragraph, where `N` and `L` are read from the
   *final document's* `Heading 3` style definition (`numId` and `ilvl`),
   not hard-coded. If `Heading 3` carries no `numPr`, warn and skip (same
   warn-and-degrade convention as a missing `Dilon Step Heading` style).

   **Why post-merge (found while planning, 2026-09-25):** `docxcompose`'s
   `Composer.add_numberings()` remaps every paragraph-level `w:numId` in
   an appended part to a fresh `w:num`, backed by a *copy* of the
   referenced `abstractNum` with a randomized `nsid`. A step carrying
   `numId 68` in Part D would land in a separate list instance from the
   headings (which keep `numId 68` through their style, untouched by the
   remap), so its `%1.%2` prefix would come from counters that never
   advance. Adding the link after the merge avoids that remap entirely.
4. No direct indent is needed: the list level's own `w:ind left=720
   hanging=720` already matches the `Dilon Step Heading` style, and the
   level's `rPr` carries only a font hint (no bold/caps), so the number
   matches the step text. No template changes are required.
5. No number fields and no tab run - the list level's own suffix supplies
   the tab.

Numbering is set directly on each paragraph rather than baked into the
`Dilon Step Heading` style in the template: the list level is already
linked to `Heading 4`, and a second style sharing it risks Word rewiring
the link. Trade-off accepted: applying "Dilon Step Heading" from Word's
style gallery to an arbitrary paragraph won't number it; pressing Enter
after an existing step will.

Restart at each Heading 3 is Word's default behavior for a lower list level
following a higher one. Two `@@@STEPS@@@` blocks under the same Heading 3
continue one count automatically.

### 4.2 Clarifications and bullets

Unchanged. Ordered clarifications keep a fresh `Dilon Step Clarification
List` numId per step (already native, so Enter already continues them).
Bullets keep their ilvl decrement.

### 4.3 Heading 4 ban

While walking paragraphs, track per Heading 3 whether a `@@@STEPS@@@` block
and/or a Heading 4 has been seen. When both occur under the same Heading 3,
in either order, raise `StepBlockError` naming the Heading 3's text, e.g.:

> `Heading 3 "Assembly" contains both a Heading 4 and a @@@STEPS@@@ block; steps share Heading 4's numbering level, so the two cannot be combined under one Heading 3`

Both orders are rejected because both corrupt numbers: a Heading 4 before
the steps shifts step numbers up; a Heading 4 after them continues from the
last step. The state resets at every Heading 3, Heading 2, and Heading 1.

A `@@@STEPS@@@` block with no Heading 3 above it since the last Heading 1
or Heading 2 (including one before any heading at all) also raises
`StepBlockError`. Heading 1 counts as a reset (added after final review):
it is off the heading list, so Word would not restart step counters there,
and steps after it would silently continue the previous Heading 3's count.
Native level-2 numbering there would render with a missing/zero middle
level, and the old field version silently reused the previous section's
Heading 3 number - both wrong.

Existing errors stay: unmatched open/close markers, a block reopened before
closing, and a block left open across a Heading 3.

### 4.4 Cross-references (`resolve_step_reference()`)

Emit literal "Step " + `REF <bookmark> \w \h`. `\w` returns the full-context
list number of the paragraph containing the bookmark, so the `{#step:label}`
bookmark no longer needs narrowing around a number span - the
`_narrow_bookmark()` call for steps is removed. Fallback if `\w` renders
wrong in manual testing: `\r`.

Anchors on nested clarifications remain unsupported.

### 4.5 `resolve_reference_markers()` field-protection workaround

`lib/dilon_docx_common.py` (~line 888) treats everything through a
paragraph's last `<w:fldSimple>` as an untouchable header, a fix written for
step-number fields. Steps no longer carry fields. During implementation,
check whether figure captions (also `fldSimple`-based) rely on the same
workaround:

- If they do, keep it and rewrite the comment to describe captions, not
  steps.
- If not, remove it.

### 4.6 Extractor (`extract_docx.py`)

- Newly compiled steps are `Dilon Step Heading` paragraphs with a native
  `numPr` and no typed number text. They must still be extracted into a
  `@@@STEPS@@@` block, not caught first by the ordinary numbered-list
  path. This is the risk area and is covered by a test-first round trip.
- `strip_stale_step_number()` stays for older field-based documents.
- Update the comment at `DILON_STEP_HEADING_STYLE` to describe both
  document generations.

### 4.7 Documentation

- `MARKDOWN_STYLING_GUIDE.md` STEPS section:
  - the Heading 4 ban;
  - steps are native Word list items: press Enter to add a step, and numbers update without F9;
  - don't press Tab/Shift+Tab on a step in Word. **Corrected after final
    review:** this spec originally claimed Tab demotes a step to a
    "2.3.1.1" sub-step. Verified in real Word (COM `ListIndent()`), Tab
    restyles the paragraph **Heading 5**, because the heading list's next
    level is linked to Heading 5; Shift+Tab gives Heading 3. The extractor
    therefore treats a Heading 5+ inside a `Dilon Step Heading` run as a
    Tab-demoted step (nested `#.` sub-step plus a review warning) rather
    than a heading that splits the procedure.
- `dilon-document-compiler/SKILL.md`: the new halting error.
- `CHANGELOG.md`: entry under the next version.
- `step_numbering.py` module docstring: remove the pointer to the
  uncommitted 2026-08-20 spec and the stale form-compiler mention.
- `tests/STYLING_TEST_TEMPLATE.md`: confirm no Heading 3 mixes Heading 4
  with steps; fix any that does.

## 5. Testing

TDD: each automated test is written and shown failing before the code
change it covers.

**Automated (python-docx / XML level):**

1. A compiled step paragraph has `numId` = Heading 3's `numId`, `ilvl` =
   Heading 3's `ilvl + 1`, and no
   `STYLEREF`/`SEQ` fields.
2. Steps under two different Heading 3s (and two blocks under one Heading 3)
   all sit on the same `numId`/`ilvl`.
3. Heading 4 then `@@@STEPS@@@` under one Heading 3 raises `StepBlockError`.
4. `@@@STEPS@@@` then Heading 4 under one Heading 3 raises `StepBlockError`.
5. Heading 4 under one Heading 3 and steps under a *different* Heading 3
   compiles cleanly.
6. A `@@@STEPS@@@` block under a Heading 2 with no Heading 3 raises
   `StepBlockError`.
7. A `[](#step:x)` reference produces a `REF step:x \w \h` field.
8. Extractor round trip: compile a steps document, extract it, and get a
   `@@@STEPS@@@` block with the step text intact and no stray numbers.
9. Existing tests asserting the field layout are rewritten to the new
   shape, not deleted.

Full suites (`run_tests.py`, `run_form_tests.py`, `run_extractor_tests.py`)
must pass.

**Manual (Word, performed by the user):** compile
`tests/STYLING_TEST_TEMPLATE.md`, open it in Word, and confirm:

- steps read "N.M.K" and restart at each Heading 3;
- Enter after a step creates the next numbered step, and following steps renumber;
- Enter on an empty step ends the list;
- after Ctrl+A, F9, step cross-references read "Step N.M.K";
- the step indent/tab layout matches the previous output (watch for step text starting at different positions: the style's 0.25" tab stop is a pre-existing quirk, fixed separately if seen).

## 6. Out of Scope

- Letting Heading 4 and steps coexist under one Heading 3.
- Cross-references to lettered clarifications.
- Baking numbering into the `Dilon Step Heading` style in the template.
- Migrating already-archived field-based documents (recompiling from
  markdown handles that).
