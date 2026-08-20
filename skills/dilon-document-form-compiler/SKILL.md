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

Syntax for the three form-only markers (`FillLine`, `FieldGrid`, `Form_Section_Header`) is documented in the `dilon-document-form-writer` skill, along with everything else that applies to a form's markdown (headings, tables, YAML front matter, `@@@STYLE@@@`/`@@@TABLE_STYLE@@@`/`@@@TABLE_COLUMNS@@@`, body-level `{{field}}` substitution). Read there before authoring or editing a form's markdown — this skill only compiles it, it doesn't explain or validate marker syntax.

## Why no title/signature/TOC

`dilon-document-compiler` always composes a signature-approval page, a revision-history table, and a title page ahead of the content, plus a table of contents from the content's headings. A form like a traveler has no meaningful version of any of that - it's a single-page (or near-single-page) table meant to be printed and filled out by hand. `TEMPLATE_Word_Base.docx` carries only header/footer and style definitions (no body content of its own), so a form gets the same running header/footer via the same Jinja2-templating mechanism `dilon-document-compiler` uses, with none of the rest.
