# Dilon Claude Tools - Codebase Knowledge

## Plugin Overview

This is a **self-hosted Claude Code plugin** for Windows environments, providing regulatory-compliant technical documentation workflows at Dilon Technologies. It bundles five Skills rather than exposing MCP tools/resources.

**Plugin Details:**
- Plugin name: `dilon-tools` (version tracked in both `VERSION.txt` and `.claude-plugin/plugin.json` - keep them in sync, see `RELEASING.md`)
- Marketplace: `dilon-claude-tools`, defined in `.claude-plugin/marketplace.json` (this repo is its own marketplace; the plugin's `source` is `./`)
- License: Internal use only (Dilon Technologies LLC)

**Distribution Workflow:**
- No package registry, no build/publish artifact step. Users install directly from this git repo via Claude Code's plugin marketplace commands:
  - `/plugin marketplace add dilontechnologies/dilon-claude-tools`
  - `/plugin install dilon-tools@dilon-claude-tools`
- Updates: `/plugin marketplace update dilon-claude-tools` then `/plugin update dilon-tools@dilon-claude-tools` - both always track the repo's default branch (`master`); `claude plugin marketplace add` has no ref-pinning flag, so merging to `master` is what actually ships an update.
- Local testing before relying on the marketplace: `/plugin marketplace add ./dilon-claude-tools` (run from the parent directory of a clone)
- See `README.md` for the full install/update/troubleshooting instructions, and `RELEASING.md` for the governed branch model (`DEV`/`BUG`/`REL` branches, CI gates, tagging, GitHub Releases) that gates what lands on `master`.

## Skills

### Skill 1: `dilon-document-writer`
**Location:** `skills/dilon-document-writer/` (`SKILL.md`, `MARKDOWN_STYLING_GUIDE.md`, `TEMPLATE_Document.md`)

**Dependencies:** none - works without running `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Creating a new document: reads `TEMPLATE_Document.md`, gathers YAML front-matter fields (title, author, department, doc_number, current_revision, department_head, signature_fields - a list of `department`/`name` approver pairs, plus an initial revision entry), refuses to overwrite an existing destination file, and writes the new file with the template's `## 1. Purpose and Scope` / `### 1.1 Purpose` / `### 1.2 Scope` sections intact.
- Editing an existing Dilon document: reads `MARKDOWN_STYLING_GUIDE.md` before editing and keeps it in context for the session, then applies edits per the guide's conventions (heading numbering, pipe/grid tables, `@@@STYLE@@@`/`@@@TABLE_STYLE@@@` markers, figure/image handling, YAML front-matter shape). Major section headings must be H2 for correct TOC generation when later compiled.
- Explicitly does not invoke Pandoc or the Python compiler - that's the `dilon-document-compiler` skill's job.

### Skill 2: `dilon-document-compiler`
**Location:** `skills/dilon-document-compiler/` (`SKILL.md`, `scripts/generate_dilon_doc.py`, `scripts/read_docx_sizes.py`, `scripts/check_deps.py`); the reference template (`templates/TEMPLATE_Word_Base.docx`) lives at the repo root, shared with `dilon-document-extractor`.

**Dependencies:** Python (>= 3.8) with `python-docx`, `docxcompose`, `pyyaml>=6.0`, `jinja2`; Pandoc on PATH. Installed via `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Runs `scripts/check_deps.py` first; if it reports any `[FAIL]`, stops and tells the user which dependency is missing (pointing at `install.ps1`) rather than attempting a partial compile.
- Invokes `scripts/generate_dilon_doc.py <input.md> <output.docx> <base_template>` with the base template argument always explicit (never relies on the script's own default template lookup).
- Front matter's `include_front_matter` boolean (default `true`) selects the compile mode: `true` produces a regulatory-compliant Word document (signature page + revision history table + content + table of contents, all built programmatically, not template-baked - only header/footer/styles come from the base template); `false` produces a header/footer-only form/traveler - no signature page, no revision table, no TOC. This flag replaced the separate `dilon-document-form-compiler` skill, retired 2026-09.
- Every `@@@FORM_FIELD:FillLine/FieldGrid/Form_Section_Header@@@` marker, in either mode, must be wrapped in `@@@FORM_SECTION@@@`/`@@@END_FORM_SECTION@@@` (`lib/dilon_form_fields.py`'s `apply_form_fields()`/`FormSectionError`) - a form-flavored section's own heading stays ordinary content outside the tag, so it's numbered and gets a TOC entry like any other section.
- Every compiled inline picture gets its aspect ratio locked for interactive resize (`lib/dilon_docx_common.py`'s `lock_image_aspect_ratios()`) - see "Image Aspect Ratio Lock" below.
- Verifies the output file exists after the script runs; reports stdout/stderr to the user on failure, or the output path on success.
- Points users lacking YAML front matter back to the `dilon-document-writer` skill.
- After a successful compile, suggests a resize-and-reapply pass when the input markdown has images/tables with no explicit size hint; `scripts/read_docx_sizes.py <resized.docx>` then reads back each image's width/height and each table's column widths (in document order, excluding the signature-approval/revision-history tables) so Claude can write `width=`/`height=` image attributes and `@@@TABLE_COLUMNS@@@` markers back into the source markdown. Matching is positional (Nth image/table in the docx = Nth in the markdown) - see "Resize-and-Reapply Workflow" below.

### Skill 3: `dilon-document-extractor`
**Location:** `skills/dilon-document-extractor/` (`SKILL.md`, `scripts/extract_docx.py`, `scripts/extract_pdf.py`, `scripts/check_deps.py`)

**Dependencies:** Python (>= 3.8) with `python-docx`, `pyyaml`, `pymupdf`. Installed via `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Runs `scripts/check_deps.py` first; if it reports any `[FAIL]`, stops and tells the user which dependency is missing rather than attempting a partial extraction.
- `.docx` path (`scripts/extract_docx.py`): reads Word paragraph styles, table structure, and header/footer to bootstrap a Dilon markdown draft - auto-detects heading levels, classifies signature-approval/revision-history tables by position against the canonical shape `create_signature_table()` (in `generate_dilon_doc.py`) generates, and pairs inline images with adjacent `Caption` paragraphs.
- `.pdf` path (`scripts/extract_pdf.py`): lower-fidelity - untagged PDFs carry no reliable style metadata, so no heading-level inference is attempted; emits body text and embedded images with a banner comment.
- Never hard-fails on ambiguous input: every uncertain classification degrades to an inline `<!-- EXTRACTOR: ... -->` comment instead of raising.
- Output always requires a cleanup pass: resolve every `EXTRACTOR` comment, sanity-check headings/tables against the source, then hand off to `dilon-document-writer` for remaining prose/structure cleanup.

### Skill 4: `dilon-document-form-writer`
**Location:** `skills/dilon-document-form-writer/` (`SKILL.md`, `TEMPLATE_Form.md`)

**Dependencies:** none - works without running `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Creating a new form document: reads `TEMPLATE_Form.md` (front matter includes `include_front_matter: false`), gathers the same YAML front-matter fields as `dilon-document-writer` (title/author/department/doc_number/current_revision/department_head/signature_fields/initial revision - `doc_number` defaults to the `FO-` form-number convention rather than `dilon-document-writer`'s narrative-doc `DD_XXX_XXXXX`), refuses to overwrite an existing destination file, and writes the new file with the template's worked example (`Form_Section_Header` + `FieldGrid` + `FillLine`, wrapped in `@@@FORM_SECTION@@@`) intact.
- Editing an existing Dilon form: reads `dilon-document-writer`'s `MARKDOWN_STYLING_GUIDE.md` (general conventions still apply to forms), then applies the three form-only markers this skill documents as the single source of truth - `FillLine`, `FieldGrid` (including its `dir=`/`rows=`/`pair=`/`label=`/`title=` annotations), and `Form_Section_Header` - each wrapped in `@@@FORM_SECTION@@@`.
- Mirrors the `dilon-document-writer` / `dilon-document-compiler` split: this skill owns markdown authoring and marker syntax for forms; `dilon-document-compiler` owns compiling that markdown to Word (via `include_front_matter: false`) and doesn't duplicate the syntax reference.
- Explicitly does not invoke Pandoc or the Python compiler - that's `dilon-document-compiler`'s job.

## Repository Structure

```
dilon-claude-tools/
├── CLAUDE.md                          # this file
├── README.md                          # install/usage/troubleshooting guide
├── RELEASING.md                       # branch/release model (REL/DEV/BUG, versioning, CI gates)
├── VERSION.txt                        # canonical version for CI - keep in sync with plugin.json
├── CHANGELOG.md
├── install.ps1                        # Python/Pandoc/pip dependency setup + Compile-DilonDoc alias
│
├── .claude-plugin/
│   ├── plugin.json                    # plugin manifest (version must match VERSION.txt)
│   └── marketplace.json               # self-hosted marketplace listing this plugin
│
├── .github/
│   ├── CODEOWNERS
│   ├── PULL_REQUEST_TEMPLATE/         # feature.md, bug-fix.md, release.md
│   └── workflows/
│       ├── ci-feature.yml             # PR -> REL/**: dependency check + all test suites
│       ├── ci-release.yml             # PR -> master: same, plus the version-tag-availability gate
│       └── release.yml                # push -> master: tags + publishes a GitHub Release
│
├── .claude/
│   ├── settings.json                  # PreToolUse hook wiring
│   └── scripts/
│       └── main-guard.sh              # blocks Claude Code edits while checked out on master
│
├── templates/                          # Shared Word reference templates
│   ├── TEMPLATE_Word_Base.docx        # header/footer + styles only, shared by both compiler skills
│   └── assets/
│       └── dilon_logo.png             # header logo, re-embedded by populate_header()
│
├── lib/
│   ├── dilon_docx_common.py           # Pandoc-conversion/styling helpers shared by the compiler and extractor
│   └── dilon_form_fields.py           # @@@FORM_FIELD@@@/@@@FORM_SECTION@@@ markers, used in both compile modes
│
├── skills/
│   ├── dilon-document-writer/
│   │   ├── SKILL.md
│   │   ├── MARKDOWN_STYLING_GUIDE.md  # Complete markdown styling reference (995 lines)
│   │   └── TEMPLATE_Document.md       # Starter document template
│   ├── dilon-document-compiler/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── generate_dilon_doc.py  # Markdown -> Word compiler (include_front_matter selects doc vs. form mode)
│   │       ├── read_docx_sizes.py     # Reads resized image/table dimensions back for the resize-and-reapply workflow
│   │       └── check_deps.py          # Preflight dependency checker
│   ├── dilon-document-extractor/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── extract_docx.py        # .docx -> Dilon markdown draft
│   │       ├── extract_pdf.py         # .pdf -> Dilon markdown draft (lower fidelity)
│   │       └── check_deps.py          # Preflight dependency checker
│   └── dilon-document-form-writer/
│       ├── SKILL.md
│       └── TEMPLATE_Form.md           # Starter template for new form documents
│
└── tests/
    ├── run_tests.py                   # direct-invocation test suite (writer/compiler)
    ├── run_form_tests.py              # direct-invocation test suite (form compiler)
    ├── run_extractor_tests.py         # direct-invocation test suite (extractor)
    ├── validate-output.py             # output validation checks
    ├── README.md
    ├── STYLING_TEST_TEMPLATE.md / .docx
    └── diagrams/                      # figures referenced by STYLING_TEST_TEMPLATE.md
```

## Document Generation (Word Compilation)

The base template (repo-root `templates/TEMPLATE_Word_Base.docx`) carries only style definitions and document properties now - its header and footer are empty containers with zero paragraphs/tables. Everything document-specific is built programmatically in Python and merged in with `docxcompose`, rather than via Jinja/`docxtpl` template substitution:

- **Header/footer**: `populate_header()` / `populate_footer()` (`lib/dilon_docx_common.py`, shared by both compiler skills) build the running header (logo + title/doc_number table with an explicit grid border, plus a "Page N of M" complex field) and footer (doc_number/rev/ECO/date line with top/bottom borders, boilerplate) fresh at compile time from the front-matter metadata dict - no Jinja fields baked into the template.
- **Signature table**: generated programmatically (`create_signature_table()` in `generate_dilon_doc.py`) from front-matter fields (author, department, department_head, and the variable-length `signature_fields` list of `department`/`name` approver pairs) and inserted into Part A - also the canonical shape `dilon-document-extractor` classifies signature tables against.
- **Revision table**: generated programmatically (`create_revision_table()`) from the markdown's `revisions` YAML list (custom column widths, gray headers, centered text).
- **Title page**: `build_title_page()` (`generate_dilon_doc.py`) builds Part C from the metadata dict - title, Author/Revised-by table, and boilerplate about ARENA PLM/master-document/approval history are all hardcoded Python + python-docx calls now; there is no separate content template file.
- **Markdown content**: converted via Pandoc, with TOC generation from H2 section headings (`markdown_to_docx()`, `include_toc` flag).
- **Image aspect ratio lock**: `lock_image_aspect_ratios()` (`lib/dilon_docx_common.py`, shared by both compiler skills) post-processes every inline picture Pandoc embeds. Pandoc's docx writer sets `picLocks`/`noChangeAspect` on the picture itself (`pic:cNvPicPr`) but never emits the enclosing `wp:cNvGraphicFramePr`/`a:graphicFrameLocks` element at all (it's schema-optional) - and that frame-level lock, not the picture-level one, is what Word actually consults for interactive corner/side-handle drag-resize. Confirmed by diffing a Pandoc-generated image against a native Word drag-and-drop insert in the same document: only the frame-level lock differed, and only the drag-dropped image resized locked. The function backfills the missing `wp:cNvGraphicFramePr`/`a:graphicFrameLocks` for every inline picture.
- **Resize-and-reapply workflow**: `dilon-document-compiler`'s `scripts/read_docx_sizes.py <resized.docx>` reads back each inline picture's width/height and each table's column widths from a document the user resized in Word, in document order, excluding the signature-approval/revision-history tables (via a local `classify_table()`, mirroring `dilon-document-extractor`'s). Claude maps the results positionally (Nth image/table in the docx = Nth in the source markdown - there's no other stable id) back onto `width=`/`height=` image attributes and `@@@TABLE_COLUMNS@@@` markers. See `dilon-document-compiler/SKILL.md`'s "Suggesting a resize pass" / "Reading resized dimensions back into the markdown" sections.

`generate_dilon_doc.py`'s `include_front_matter: false` mode reuses `populate_header()`/`populate_footer()` and `lock_image_aspect_ratios()` against the same base template but skips the signature table, revision table, TOC, and resize-and-reapply workflow entirely - what `dilon-document-form-compiler` did as a separate skill before being retired. In both modes, `lib/dilon_form_fields.py`'s `apply_form_fields()` postprocesses every `@@@FORM_FIELD:FillLine/FieldGrid/Form_Section_Header@@@` marker found inside a `@@@FORM_SECTION@@@`...`@@@END_FORM_SECTION@@@` range - `FormSectionError` halts compilation for a marker outside one, or a malformed range.

`TEMPLATE_Document.md` (in `dilon-document-writer`) provides the starter markdown with the full YAML front-matter shape and section templates for new documents.

## Styling Guide

**File:** `skills/dilon-document-writer/MARKDOWN_STYLING_GUIDE.md` (995 lines)

Covers YAML front matter requirements, heading conventions/numbering, table formatting (pipe and grid tables, custom `DilonTable_List`/`DilonTable_Chart` styles), figure/image handling (including sizing via Pandoc's `{width=...}`/`{height=...}` image attributes), lists, code blocks, links, notes/callouts, custom paragraph styles via `@@@STYLE@@@` markers, footnote formatting, and a complete style reference table.

## Key Architectural Patterns

1. **Skill Modularity:** Each skill is self-contained (`SKILL.md` + any scripts/docs it needs) and independently installable in concept - `dilon-document-writer` and `dilon-document-form-writer` have zero runtime dependencies, `dilon-document-compiler` and `dilon-document-extractor` depend on Python (and Pandoc, for the compiler). Both document families follow the same authoring/compiling split: `dilon-document-writer`/`dilon-document-form-writer` own markdown authoring and marker syntax, `dilon-document-compiler` owns compiling both to Word (narrative and form/traveler alike, selected by `include_front_matter`) without duplicating that syntax reference - `dilon-document-form-compiler` was retired in favor of this one flag. The Word reference templates are shared at the repo root since both `dilon-document-compiler` and `dilon-document-extractor` reference their canonical shape.
2. **Preflight Validation:** The compiler skill checks dependencies (`check_deps.py`) before attempting work, rather than failing partway through.
3. **Explicit Arguments:** The compiler script is always invoked with all three arguments spelled out (input, output, base template) rather than relying on internal defaults.
4. **Template Inheritance:** Word styles cascade from the base template through to the assembled document; header, footer, signature table, revision table, and title page are all generated programmatically in Python against that template's style definitions rather than being template-baked.
5. **Self-Hosted Distribution:** The repo is both the source and its own plugin marketplace - no external registry or publish pipeline.

## Dependencies

**For `dilon-document-writer`:** none.

**For `dilon-document-compiler`:**
- Python >= 3.8
- Pandoc (on PATH)
- Python packages: `python-docx`, `docxcompose`, `pyyaml>=6.0`, `jinja2`

**For `dilon-document-form-compiler`:** same as `dilon-document-compiler`.

**For `dilon-document-extractor`:**
- Python >= 3.8
- Python packages: `python-docx`, `pyyaml`, `pymupdf`

**For `dilon-document-form-writer`:** none.

`install.ps1` (repo root, run as Administrator) installs Python/Pandoc via winget if missing, installs the pip packages above (including `pymupdf`), and installs a `Compile-DilonDoc` / `dilonc` PowerShell alias for compiling documents outside of Claude Code.
