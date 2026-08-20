---
name: dilon-document-form-writer
description: Create new Dilon form/traveler documents from the standard form template, and apply the FillLine/FieldGrid/Form_Section_Header markdown markers when editing an existing Dilon form's markdown. Use when asked to create a new Dilon form/traveler, draft a form stub, or write/edit a form document's fields and sections - as opposed to dilon-document-writer, which is for narrative documents (work instructions, SOPs, specs).
---

# Dilon Document Form Writer

Helps create and maintain Dilon Technologies form/traveler markdown documents - single-page (or near-single-page) documents meant to be printed and filled out by hand, as opposed to the narrative documents `dilon-document-writer` handles.

## Creating a new form document

1. Read `TEMPLATE_Form.md` in this skill's directory.
2. Ask the user (or use sensible defaults below) for the YAML front-matter fields:
   - `title` (default: "Form Title")
   - `author` (default: "Author Name")
   - `department` (default: "--")
   - `doc_number` (default: "FO-XXXXX" - forms use the `FO-` prefix convention, not `dilon-document-writer`'s narrative-doc `DD_XXX_XXXXX`)
   - `current_revision` (default: "00")
   - `regulatory_rep` (default: "--")
   - `quality_rep` (default: "--")
   - `department_head` (default: "--")
   - Initial revision entry: `revision_description` (default: "Initial release"), `eco_number` (default: "ECO-TBD"), `eco_date` (default: "YYYY-MM-DD")
3. Substitute these into the template's YAML front matter. The first entry in `revisions` always mirrors `current_revision` for its `number` field.
4. Before writing, check whether the destination file already exists — refuse and tell the user if it does.
5. Write the new file with the substituted front matter and the template's worked example (a `Form_Section_Header`, a `FieldGrid` block, and a `FillLine`) intact — replace the bracketed placeholders with the form's real fields once the user is ready.

## Editing an existing Dilon form

1. Read `dilon-document-writer`'s `MARKDOWN_STYLING_GUIDE.md` before making edits, if it isn't already in context for this conversation — every general convention documented there (headings, tables, YAML front-matter shape, `@@@STYLE@@@`/`@@@TABLE_STYLE@@@`/`@@@TABLE_COLUMNS@@@` markers, body-level `{{field}}` substitution) still applies to forms. Keep it in context for the remainder of the editing session.
2. Apply the three form-only markers documented below as needed.

### Fill-in-the-blank line (`FillLine`)

A label followed by a blank that fills to the true right edge of the page or the enclosing table cell, computed at compile time (not hand-counted underscores):

```markdown
@@@FORM_FIELD:FillLine@@@Work Order:@@@END_FORM_FIELD@@@
```

Place it on its own line as a standalone paragraph (body-level) or as the sole content of a table cell. The marker is removed and replaced with the label followed by a right-aligned, underscore-leadered tab stop.

Two optional annotations, `[key=value]` appended directly after the label text (no space):

- `width=NNin` — a custom blank length instead of filling to the end of the page/cell. Clamped to the available width (with a warning) if it exceeds it.
- `lines=N` — adds `N - 1` extra full-width blank lines below the label line. When `lines > 1`, `width=` is ignored (every line, including the label's own, spans the full available width).

```markdown
@@@FORM_FIELD:FillLine@@@Work Order:[width=3in]@@@END_FORM_FIELD@@@
@@@FORM_FIELD:FillLine@@@Notes:[lines=4]@@@END_FORM_FIELD@@@
```

### Field grid (`FieldGrid`)

A grid of label + fillable-blank pairs, built entirely by the compiler (not through Pandoc's markdown tables, which can't express the per-cell borders this needs) — for dense field-entry sections like a traveler's Work Order/Date/Technician block:

```markdown
@@@FORM_FIELD:FieldGrid@@@
Work Order: | Date:
5mm GAGG Crystal Lot: | Technician:
Carrier Board Assy Lot:
Epoxy Lot # and Expiration:[label=70] | Alignment Fixture:
Cure Temp:[pair=60] | Start Time:[pair=40]
Notes: {dir=v,rows=3}
@@@END_FORM_FIELD@@@
```

Each non-blank line is one **row**, rendered as its own bordered Word table (`Table Grid` style) stacked directly against its neighbors so the whole block reads as one continuous grid. Pairs on a line are separated by ` | ` — each pair is one label cell plus one blank cell to fill in.

**Per-pair annotation** — `Label text[key=value,...]`, directly after the label text:
- `label=NN` — (only meaningful when the row is `dir=h`, the default) this pair's label sub-cell takes `NN`% of the pair's width; the blank gets the complement. Default `50`.
- `pair=NN` — this pair's share of the row's total width, as a percentage. Pairs without `pair=` split whatever's left evenly. Default (nothing declared): equal split across all pairs.
- `rows=N` — per-pair override of the row's `rows=` default (see below) — how many lines tall this pair's blank cell is.

**Row-level annotation** — ` {key=value,...}` trailing the whole line, distinguished from per-pair annotations by curly braces instead of square brackets:
- `dir=h` (default) or `dir=v` — orientation for **every pair on the row** (a row can't mix horizontal and vertical pairs; put a vertical field on its own line). `h`: label and blank side by side. `v`: label on top, blank below, both spanning the pair's full width.
- `rows=N` — default blank-cell height (in lines) for every pair on the row; default `1`.
- `title=true` — makes the row a **title row**: no input/blank cell, just a bold label spanning the row's full width. Truthy values (case-insensitive): `true`, `t`, `1`, `yes`; anything else (including absent) is a normal row. Use it to break a `FieldGrid` block into labeled sub-sections without leaving the grid.

**Block-level max width** — optional `:<width>in` suffix on the opening marker, e.g. `@@@FORM_FIELD:FieldGrid:6.5in@@@`. Defaults to the available page/cell width; clamped (with a warning) if the given value exceeds it.

Title-row specifics:
- Only the first `|`-separated pair token on a title row is used; any additional tokens are dropped with a printed warning.
- `pair=` and `label=` on a title row's label token are ignored (with a warning) — there's no percentage split or label/blank split with only one column.
- `dir=` is accepted on a title row but has no visible effect (nothing to orient) — not a mistake, no warning.
- `rows=N` still applies: it adds `N - 1` blank paragraphs below the bold label, inside the same cell.

```markdown
@@@FORM_FIELD:FieldGrid@@@
Work Order: | Date:
Assembly Prep {title=true}
Technician: | Notes:
@@@END_FORM_FIELD@@@
```

`FieldGrid` is top-level body content only — it isn't supported inside a markdown table cell (the marker is left as-is with a warning if found there).

### Section header (`Form_Section_Header`)

An alternative to a Pandoc `#`/`##`/`###` markdown heading, purpose-built for forms: a single, automatically-numbered heading, restyled with the template's `Form Section Header` paragraph style. Use it to mark the start of a chunk of a form meant to be completed in full before moving on — unlike `#` headings, it isn't hooked up to numbering-list linkage or a table of contents (forms have neither):

```markdown
@@@FORM_FIELD:Form_Section_Header@@@Assembly Prep@@@END_FORM_FIELD@@@
```

Renders as `Section 1 - Assembly Prep`. The number increments once per `Form_Section_Header` marker found, in document order, starting at 1 — there's no nesting or reset. If the compiled document doesn't yet have a `Form Section Header` style (e.g. an older `TEMPLATE_Word_Base.docx`), the heading text still renders with its number, just without the style, with a printed warning — never a hard failure.

`Form_Section_Header` is top-level body content only — it isn't supported inside a markdown table cell (the marker is left as-is with a warning if found there).

## Next step

Once content is ready, compiling it to a Word document is handled by the separate `dilon-document-form-compiler` skill — don't attempt to invoke Pandoc or the Python compiler from this skill.
