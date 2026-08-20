---
name: dilon-document-form-compiler
description: Compile a Dilon form's markdown (rich YAML front matter, no title/signature/TOC content) into a Word document with a running header/footer only. Use when asked to compile, convert, or export a Dilon form/traveler markdown document to Word/.docx - as opposed to dilon-document-compiler, which is for narrative documents that need a title page, signature page, and table of contents.
---

# Dilon Document Form Compiler

Wraps `generate_dilon_form.py` to convert a form's markdown (with the same rich Dilon YAML front matter as any other Dilon document) into a formatted `.docx` carrying only a running header/footer (title/doc number/revision) - no title page, no signature-approval page, no table of contents. Use `dilon-document-compiler` instead for narrative documents (work instructions, SOPs, specs) that need those.

## Before compiling

Run the dependency check first:

```
python scripts/check_deps.py
```

If it reports any `[FAIL]`, stop and tell the user exactly which dependency is missing and that `install.ps1` (repo root) can install Python/Pandoc/pip packages automatically. Do not attempt compilation with missing dependencies.

## Compiling

```
python scripts/generate_dilon_form.py <input.md> <output.docx> <base_template>
```

- `<input.md>`: the form's markdown file, with the same YAML front-matter shape as `dilon-document-compiler` expects (see its `SKILL.md`) - keep it rich (`author`/`regulatory_rep`/`quality_rep`/`department_head`/`revisions` and all) even though the base template's header only renders `title`/`doc_number`/`current_revision`; those fields are used elsewhere (approval tracking, audits).
- `<output.docx>`: defaults to the same name as the input with a `.docx` extension if not specified.
- `<base_template>`: defaults to repo-root `templates/TEMPLATE_Word_Base.docx` - the same header/footer/styles template `dilon-document-compiler` uses. There is no separate form-only template: neither skill's template carries body content of its own, so both share the one file.

After the script exits, verify the output file now exists. Report the script's stdout/stderr to the user on failure; report the output path on success.

## Form-specific markdown

Everything documented in `dilon-document-writer`'s `MARKDOWN_STYLING_GUIDE.md` applies (headings, tables, `@@@STYLE@@@`/`@@@TABLE_STYLE@@@`/`@@@TABLE_COLUMNS@@@`, body-level `{{field}}` substitution), plus three form-only markers:

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

## Why no title/signature/TOC

`dilon-document-compiler` always composes a signature-approval page, a revision-history table, and a title page ahead of the content, plus a table of contents from the content's headings. A form like a traveler has no meaningful version of any of that - it's a single-page (or near-single-page) table meant to be printed and filled out by hand. `TEMPLATE_Word_Base.docx` carries only header/footer and style definitions (no body content of its own), so a form gets the same running header/footer via the same Jinja2-templating mechanism `dilon-document-compiler` uses, with none of the rest.
