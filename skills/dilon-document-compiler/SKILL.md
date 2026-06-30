---
name: dilon-document-compiler
description: Compile a Dilon-formatted markdown file (with YAML front matter) into a regulatory-compliant Word document, with signature page, revision history table, and table of contents. Use when asked to compile, convert, or export a Dilon markdown document to Word/.docx.
---

# Dilon Document Compiler

Wraps the Dilon Document Compiler Python script to convert a markdown file with Dilon YAML front matter into a formatted .docx (signature page + revision table + title page + content with TOC).

## Before compiling

Run the dependency check first:

```
python scripts/check_deps.py
```

(Run from this skill's directory, or pass the full path to `check_deps.py`.)

If it reports any `[FAIL]` line, stop and tell the user exactly which dependency is missing and that `install.ps1` (repo root) can install Python/Pandoc/pip packages automatically. Do not attempt compilation with missing dependencies — it will fail partway through and leave temp files behind.

## Compiling

Invoke the script with explicit template paths — always pass all four arguments, never rely on the script's own default template lookup:

```
python scripts/generate_dilon_doc.py <input.md> <output.docx> <signature_template> <content_template>
```

- `<input.md>`: the markdown file to compile (must have YAML front matter — if it doesn't, point the user at the `dilon-document-writer` skill first).
- `<output.docx>`: defaults to the same name as the input with a `.docx` extension if the user doesn't specify one.
- `<signature_template>`: defaults to `templates/TEMPLATE_Word_Signature.docx` in this skill's directory, unless the user supplies a custom one.
- `<content_template>`: defaults to `templates/TEMPLATE_Word_Content.docx` in this skill's directory, unless the user supplies a custom one.

After the script exits, verify the output file now exists. Report the script's stdout/stderr to the user on failure; report the output path on success.

## Input format reference

The input markdown needs YAML front matter shaped like:

```yaml
---
title: "Document Title"
author: "Author Name"
department: "Engineering"
doc_number: "DD_XXX_XXXXX"
current_revision: "01"
regulatory_rep: "Name"
quality_rep: "Name"
department_head: "Name"
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
