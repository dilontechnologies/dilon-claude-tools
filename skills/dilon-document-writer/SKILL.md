---
name: dilon-document-writer
description: Create new Dilon Technologies documents from the standard template, and apply Dilon markdown styling conventions (headings, tables, YAML front matter, custom style markers) when editing or adding content to existing Dilon-formatted markdown documents. Use when asked to create a new Dilon doc, draft a stub, or write/edit sections of a document that has Dilon YAML front matter.
---

# Dilon Document Writer

Helps create and maintain Dilon Technologies markdown documents in the company's regulatory-compliant format (ISO 62304 / FDA submission ready).

## Creating a new document

1. Read `TEMPLATE_Document.md` in this skill's directory.
2. Ask the user (or use sensible defaults below) for the YAML front-matter fields:
   - `title` (default: "Document Title")
   - `author` (default: "Author Name")
   - `department` (default: "--")
   - `doc_number` (default: "DD_XXX_XXXXX")
   - `current_revision` (default: "00")
   - `regulatory_rep` (default: "--")
   - `quality_rep` (default: "--")
   - `department_head` (default: "--")
   - Initial revision entry: `revision_description` (default: "Initial release"), `eco_number` (default: "ECO-TBD"), `eco_date` (default: "YYYY-MM-DD")
3. Substitute these into the template's YAML front matter. The first entry in `revisions` always mirrors `current_revision` for its `number` field.
4. Before writing, check whether the destination file already exists — refuse and tell the user if it does.
5. Write the new file with the substituted front matter and the template's `## Purpose and Scope` / `### Purpose` / `### Scope` sections intact.

## Editing an existing Dilon document

1. Read `MARKDOWN_STYLING_GUIDE.md` in this skill's directory before making edits, if it isn't already in context for this conversation. Keep it in context for the remainder of the editing session — don't re-derive formatting rules from memory once it falls out of context.
2. Apply edits per the user's request, following the guide's conventions: heading structure (no manual section numbers — Word auto-numbers Heading 2/3/4), pipe/grid table formatting, custom `@@@STYLE@@@`/`@@@TABLE_STYLE@@@` markers, figure/image handling, and YAML front-matter shape.
3. Major section headings must be H2 (`##`) — required for correct table-of-contents generation when the document is later compiled to Word by the `dilon-document-compiler` skill.

## Next step

Once content is ready, compiling it to a Word document is handled by the separate `dilon-document-compiler` skill — don't attempt to invoke Pandoc or the Python compiler from this skill.
