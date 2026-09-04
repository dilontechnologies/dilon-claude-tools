---
name: dilon-document-compiler
description: Compile a Dilon-formatted markdown file (with YAML front matter) into a Word document - a regulatory-compliant document with signature page, revision history table, and table of contents by default, or a header/footer-only form/traveler when the front matter sets include_front_matter: false. Use when asked to compile, convert, or export a Dilon markdown document or form/traveler to Word/.docx.
---

# Dilon Document Compiler

Wraps the Dilon Document Compiler Python script to convert a markdown file with Dilon YAML front matter into a formatted .docx. By default (`include_front_matter: true`, or the field omitted) this is a full narrative document: signature page + revision table + content with TOC. With `include_front_matter: false` in the front matter, it compiles a form/traveler instead - running header/footer only, no signature page, no TOC - the same output `dilon-document-form-compiler` used to produce before that skill was retired in favor of this one flag.

## Before compiling

Run the dependency check first:

```
python scripts/check_deps.py
```

(Run from this skill's directory, or pass the full path to `check_deps.py`.)

If it reports any `[FAIL]` line, stop and tell the user exactly which dependency is missing and that `install.ps1` (repo root) can install Python/Pandoc/pip packages automatically. Do not attempt compilation with missing dependencies — it will fail partway through and leave temp files behind.

## Compiling

Invoke the script with an explicit base template path — never rely on the script's own default template lookup:

```
python scripts/generate_dilon_doc.py <input.md> <output.docx> <base_template>
```

- `<input.md>`: the markdown file to compile (must have YAML front matter — if it doesn't, point the user at the `dilon-document-writer` skill first).
- `<output.docx>`: optional. If omitted, the script computes `<doc_number> Rev <current_revision>.docx` next to the input from the front matter (e.g. `DD_001_00001 Rev 01.docx`) — pass an explicit path only when the user wants a different name/location. Compilation halts with a clear error if `doc_number`/`current_revision` are missing and no output path was given.
- `<base_template>`: defaults to `templates/TEMPLATE_Word_Base.docx` at the repo root, unless the user supplies a custom one. Header/footer/styles only — the title page, signature-approval table, and revision table are all built programmatically by the script and inserted around the base template's header/footer.

After the script exits, verify the output file now exists. Report the script's stdout/stderr to the user on failure; report the output path on success.

Compilation halts (non-zero exit, clear error message) rather than producing a silently-broken document for:
- An ordered (`#.`) list nested more than three levels deep
- A `@@@CONTINUE:#list:name@@@` marker whose `name` has no matching `[]{#list:name}` anchor, or a `[]{#list:name}` anchor declared more than once
- A malformed `@@@STEPS@@@`/`@@@END_STEPS@@@` pairing (unclosed or nested)
- A `[](#fig:label)`, `[](#sec:label)`, or `[](#step:label)` reference with no matching `{#fig:label}`/`{#sec:label}`/`{#step:label}` anchor anywhere in the document, or such an anchor declared more than once

## Suggesting a resize pass

After a successful compile, scan the **input markdown** for images and tables that have no explicit size:
- An image (`![...](...)`) whose trailing `{...}` attribute block (if any) has neither `width=` nor `height=`.
- A pipe/grid table with no `@@@TABLE_COLUMNS:...@@@` marker immediately before it.

If any are found, suggest the resize-and-reapply workflow below - don't run it unprompted:

> "This document has N image(s)/table(s) with no explicit size, so they compiled at their default/native size. If you'd like to fine-tune the layout, open the .docx in Word, resize them there, save, and let me know - I can read the new sizes back and write them into the markdown so they stick on the next compile."

## Reading resized dimensions back into the markdown

When the user asks to apply sizes from a document they resized in Word:

```
python scripts/read_docx_sizes.py <resized.docx>
```

This prints a JSON array of `{"type": "image", "index": N, "width_in": ..., "height_in": ...}` and `{"type": "table", "index": N, "column_widths_in": [...]}` entries - `index` is 0-based per type, in document order, and already excludes the signature-approval/revision-history tables.

Before writing anything back:
1. Count the images and tables in the **source markdown** (the same ones the "no explicit size" scan above looks for, plus any that already had a size). Compare against the script's image/table counts.
2. If the counts don't match, stop and tell the user - the Nth image/table in the docx no longer corresponds to the Nth image/table in the markdown (content was likely added, removed, or reordered since compiling), and applying sizes positionally would silently mislabel them. Ask the user to confirm which markdown element each entry corresponds to, or to recompile from the current markdown first.
3. If the counts match, apply positionally: for each image entry, set `width=` and `height=` (e.g. `width=4in height=2in`, using that entry's `width_in`/`height_in` values) in that image's trailing `{...}` block (add the block if it doesn't have one yet, preserving any existing `#fig:` id); for each table entry, insert or replace the `@@@TABLE_COLUMNS:w1,w2,...@@@` marker immediately before that table using that entry's `column_widths_in` values.
4. Report what was changed so the user can review before recompiling.

## Input format reference

The input markdown needs YAML front matter shaped like:

```yaml
---
title: "Document Title"
author: "Author Name"
department: "Engineering"
doc_number: "DD_XXX_XXXXX"
current_revision: "01"
department_head: "Name"
signature_fields:
  - department: "Regulatory"
    name: "Name"
  - department: "Quality"
    name: "Name"
revisions:
  - number: "00"
    description: "Initial release"
    eco_number: "ECO-TBD"
    eco_date: "2026-01-01"
  - number: "01"
    description: "Updated section 2"
    eco_number: "ECO-1234"
    eco_date: "2026-03-01"
---
```

Major section headings in the body must be H2 (`##`) for correct table-of-contents generation.

## Compiling a form/traveler (no signature page, no TOC)

Set `include_front_matter: false` in the front matter to compile a header/footer-only form/traveler instead of a full narrative document - no signature-approval page, no revision table, no table of contents. This is what `dilon-document-form-compiler` used to do as a separate skill; that skill has been retired in favor of this one flag on this compiler.

Every `@@@FORM_FIELD:...@@@` marker (`FillLine`, `FieldGrid`, `Form_Section_Header` - syntax documented in `dilon-document-form-writer`) must be wrapped in `@@@FORM_SECTION@@@`/`@@@END_FORM_SECTION@@@`, regardless of `include_front_matter`. A pure form document wraps its entire body in one `@@@FORM_SECTION@@@` pair; a narrative document (`include_front_matter: true`) can embed one or more form sections inside otherwise-normal content - the section's own heading (e.g. `## Test Report`) stays ordinary markdown, outside/above the `@@@FORM_SECTION@@@` tag, so it's numbered and gets a TOC entry like any other section:

```markdown
## Test Report

@@@FORM_SECTION@@@

@@@FORM_FIELD:FieldGrid@@@
Tested By: | Date:
@@@END_FORM_FIELD@@@

@@@END_FORM_SECTION@@@
```

A `@@@FORM_FIELD:...@@@` marker found outside any `@@@FORM_SECTION@@@` range, or a malformed range (unclosed, unmatched `@@@END_FORM_SECTION@@@`, or nested `@@@FORM_SECTION@@@`), halts compilation with a clear error rather than silently passing the marker through as literal text.
