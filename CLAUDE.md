# Dilon Claude Tools - Codebase Knowledge

## Plugin Overview

This is a **self-hosted Claude Code plugin** for Windows environments, providing regulatory-compliant technical documentation workflows at Dilon Technologies. It bundles two Skills rather than exposing MCP tools/resources.

**Plugin Details:**
- Plugin name: `dilon-tools` (version 2.0.0), defined in `.claude-plugin/plugin.json`
- Marketplace: `dilon-claude-tools`, defined in `.claude-plugin/marketplace.json` (this repo is its own marketplace; the plugin's `source` is `./`)
- License: Internal use only (Dilon Technologies LLC)

**Distribution Workflow:**
- No package registry, no publish step. Users install directly from this git repo via Claude Code's plugin marketplace commands:
  - `/plugin marketplace add dilontechnologies/dilon-claude-tools`
  - `/plugin install dilon-tools@dilon-claude-tools`
- Updates: `/plugin marketplace update dilon-claude-tools` then `/plugin update dilon-tools@dilon-claude-tools`
- Local testing before relying on the marketplace: `/plugin marketplace add ./dilon-claude-tools` (run from the parent directory of a clone)
- See `README.md` for the full install/update/troubleshooting instructions.

## Skills

### Skill 1: `dilon-document-writer`
**Location:** `skills/dilon-document-writer/` (`SKILL.md`, `MARKDOWN_STYLING_GUIDE.md`, `TEMPLATE_Document.md`)

**Dependencies:** none - works without running `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Creating a new document: reads `TEMPLATE_Document.md`, gathers YAML front-matter fields (title, author, department, doc_number, current_revision, regulatory_rep, quality_rep, department_head, plus an initial revision entry), refuses to overwrite an existing destination file, and writes the new file with the template's `## 1. Purpose and Scope` / `### 1.1 Purpose` / `### 1.2 Scope` sections intact.
- Editing an existing Dilon document: reads `MARKDOWN_STYLING_GUIDE.md` before editing and keeps it in context for the session, then applies edits per the guide's conventions (heading numbering, pipe/grid tables, `@@@STYLE@@@`/`@@@TABLE_STYLE@@@` markers, figure/image handling, YAML front-matter shape). Major section headings must be H2 for correct TOC generation when later compiled.
- Explicitly does not invoke Pandoc or the Python compiler - that's the `dilon-document-compiler` skill's job.

### Skill 2: `dilon-document-compiler`
**Location:** `skills/dilon-document-compiler/` (`SKILL.md`, `scripts/generate_dilon_doc.py`, `scripts/check_deps.py`, `templates/TEMPLATE_Word_Signature.docx`, `templates/TEMPLATE_Word_Content.docx`)

**Dependencies:** Python (>= 3.8) with `python-docx`, `python-docx-template`, `docxcompose`, `pyyaml>=6.0`; Pandoc on PATH. Installed via `install.ps1`.

**Capabilities (per `SKILL.md`):**
- Runs `scripts/check_deps.py` first; if it reports any `[FAIL]`, stops and tells the user which dependency is missing (pointing at `install.ps1`) rather than attempting a partial compile.
- Invokes `scripts/generate_dilon_doc.py <input.md> <output.docx> <signature_template> <content_template>` with all four arguments always explicit (never relies on the script's own default template lookup).
- Produces a regulatory-compliant Word document: signature page + revision history table + title page/content + table of contents, from a markdown file with Dilon YAML front matter.
- Verifies the output file exists after the script runs; reports stdout/stderr to the user on failure, or the output path on success.
- Points users lacking YAML front matter back to the `dilon-document-writer` skill.

## Repository Structure

```
dilon-claude-tools/
├── CLAUDE.md                          # this file
├── README.md                          # install/usage/troubleshooting guide
├── CHANGELOG.md
├── install.ps1                        # Python/Pandoc/pip dependency setup + Compile-DilonDoc alias
│
├── .claude-plugin/
│   ├── plugin.json                    # plugin manifest
│   └── marketplace.json               # self-hosted marketplace listing this plugin
│
├── skills/
│   ├── dilon-document-writer/
│   │   ├── SKILL.md
│   │   ├── MARKDOWN_STYLING_GUIDE.md  # Complete markdown styling reference (995 lines)
│   │   └── TEMPLATE_Document.md       # Starter document template
│   └── dilon-document-compiler/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── generate_dilon_doc.py  # Markdown -> Word compiler
│       │   └── check_deps.py          # Preflight dependency checker
│       └── templates/
│           ├── TEMPLATE_Word_Signature.docx
│           └── TEMPLATE_Word_Content.docx
│
└── tests/
    ├── run_tests.py                   # direct-invocation test suite
    ├── validate-output.py             # output validation checks
    ├── README.md
    ├── STYLING_TEST_TEMPLATE.md / .docx
    └── diagrams/                      # figures referenced by STYLING_TEST_TEMPLATE.md
```

## Document Generation (Word Compilation)

The `dilon-document-compiler` skill assembles Word documents from several parts:

- **Signature template** (`templates/TEMPLATE_Word_Signature.docx`): master document with style definitions, a Jinja2-templated signature approval table, and document properties (title, author, department, doc_number, current_revision, regulatory_rep, quality_rep, department_head).
- **Revision table**: generated programmatically from the markdown's `revisions` YAML list (custom column widths, gray headers, centered text).
- **Content template** (`templates/TEMPLATE_Word_Content.docx`): title page and content wrapper (author/revision info).
- **Markdown content**: converted via Pandoc, with TOC generation from H2 section headings.

`TEMPLATE_Document.md` (in `dilon-document-writer`) provides the starter markdown with the full YAML front-matter shape and section templates for new documents.

## Styling Guide

**File:** `skills/dilon-document-writer/MARKDOWN_STYLING_GUIDE.md` (995 lines)

Covers YAML front matter requirements, heading conventions/numbering, table formatting (pipe and grid tables, custom `DilonTable_List`/`DilonTable_Chart` styles), figure/image handling, lists, code blocks, links, notes/callouts, custom paragraph styles via `@@@STYLE@@@` markers, footnote formatting, and a complete style reference table. It also retains a PlantUML diagram-generation reference (section 4.3) for documents that hand-embed PlantUML diagrams, even though this repo no longer ships PlantUML tooling itself.

## Key Architectural Patterns

1. **Skill Modularity:** Each skill is self-contained (`SKILL.md` + any scripts/templates/docs it needs) and independently installable in concept - `dilon-document-writer` has zero runtime dependencies, `dilon-document-compiler` depends on Python/Pandoc.
2. **Preflight Validation:** The compiler skill checks dependencies (`check_deps.py`) before attempting work, rather than failing partway through.
3. **Explicit Arguments:** The compiler script is always invoked with all four arguments spelled out (input, output, signature template, content template) rather than relying on internal defaults.
4. **Template Inheritance:** Word styles cascade from the signature master template through to the assembled document.
5. **Self-Hosted Distribution:** The repo is both the source and its own plugin marketplace - no external registry or publish pipeline.

## Dependencies

**For `dilon-document-writer`:** none.

**For `dilon-document-compiler`:**
- Python >= 3.8
- Pandoc (on PATH)
- Python packages: `python-docx`, `python-docx-template`, `docxcompose`, `pyyaml>=6.0`

`install.ps1` (repo root, run as Administrator) installs Python/Pandoc via winget if missing, installs the pip packages above, and installs a `Compile-DilonDoc` / `dilonc` PowerShell alias for compiling documents outside of Claude Code.
