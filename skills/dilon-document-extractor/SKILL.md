---
name: dilon-document-extractor
description: Bootstrap a Dilon markdown draft (YAML front matter + body + extracted images) from an existing Word or PDF document. Use when asked to convert, migrate, or extract an existing .docx/.pdf into Dilon markdown, or to bootstrap a draft for the dilon-document-writer/dilon-document-compiler pipeline from a document that predates it.
---

# Dilon Document Extractor

Produces a best-effort Dilon markdown draft from an existing Word (`.docx`) or PDF (`.pdf`) document, so a human/Claude cleanup pass via `dilon-document-writer` doesn't have to start from a blank page.

## Before extracting

Run the dependency check first:

```
python scripts/check_deps.py
```

If it reports any `[FAIL]`, stop and tell the user which dependency is missing and that `install.ps1` (repo root) can install it. Do not attempt extraction with missing dependencies.

## Extracting

For a `.docx` source (the primary, higher-fidelity path):

```
python scripts/extract_docx.py <input.docx> <output_dir>
```

For a `.pdf` source (explicitly lower-fidelity - see below):

```
python scripts/extract_pdf.py <input.pdf> <output_dir>
```

Both write `<output_dir>/<slug>.md` and `<output_dir>/images/`. Report the script's stdout/stderr to the user, including any `[WARN]` lines - the script never fails outright on ambiguous input, it degrades to warnings instead.

## After extracting - required cleanup pass

The script does mechanical extraction only; it does not make judgment calls. Before treating the output as ready for `dilon-document-compiler`:

1. Read `MARKDOWN_STYLING_GUIDE.md` (in the `dilon-document-writer` skill directory) if it isn't already in context, and keep it in context for the cleanup pass.
2. Search the draft for `<!-- EXTRACTOR: ... -->` comments and resolve each one - they flag exactly the things the script wasn't confident about (mismatched signature-approval role labels, orphan captions, suspicious heading text, disagreeing header/footer vs. body metadata).
3. Sanity-check the heading levels and table classification against the source document.
4. Hand off to a normal `dilon-document-writer` editing pass for any remaining prose/structure cleanup.

## `.docx` vs `.pdf` fidelity

The `.docx` path reads Word's paragraph styles, table structure, and header/footer directly, so heading levels, table roles, and figure captions are inferred with reasonable confidence (still always double-checked in the cleanup pass above). The `.pdf` path has no such structure available - untagged PDFs carry no reliable style metadata - so it does **not** attempt heading-level inference at all. Every PDF-derived draft starts with a `<!-- EXTRACTOR: PDF source ... -->` banner comment and needs substantially more manual cleanup than a `.docx`-derived one; treat it as a rough starting point, not a near-final draft.
