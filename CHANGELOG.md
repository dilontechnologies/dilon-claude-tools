# Changelog

All notable changes to the Dilon Claude Tools MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-08-26

### Fixed
- Install docs: clarified that Claude may run `git clone` itself - only `install.ps1` (elevated terminal, machine-wide winget installs) must be run by the user

## [2.0.0] - 2026-08-26

### Added
- `dilon-document-extractor` skill - bootstraps a Dilon markdown draft from an existing Word (`extract_docx.py`) or PDF (`extract_pdf.py`) document, classifying signature/revision tables by shape and pairing inline images with adjacent `Caption` paragraphs
- `dilon-document-form-writer` skill - creates new Dilon form/traveler documents and documents the form-only markdown markers (`FillLine`, `FieldGrid`, `Form_Section_Header`) as the single source of truth for their syntax
- STEPS numbering rewritten as field-based, reset per Heading 3, with step/figure/section cross-references unified under a shared `[](#TYPE:label)` resolution framework
- Ordered-list handling: a three-level nesting cap, `Dilon Step List` style remap, and `@@@CONTINUE:#list:name@@@` continuation support for interrupted lists
- Variable-length signature approvers - `signature_fields` is now an arbitrary-length list of `department`/`name` pairs instead of a fixed shape
- Resize-and-reapply workflow: `dilon-document-compiler` suggests a Word resize pass for images/tables with no explicit size, and `scripts/read_docx_sizes.py` reads the result back into `width=`/`height=` image attributes and `@@@TABLE_COLUMNS@@@` markers
- Governed release process (this repo now follows the `nav3-repo-template` branch/release model) - see `RELEASING.md`, `.github/workflows/`, and `.claude/scripts/main-guard.sh`

### Fixed
- Compiled images now actually lock their aspect ratio on resize - Pandoc sets picture-level `picLocks` but never emits the frame-level `wp:cNvGraphicFramePr`/`a:graphicFrameLocks` Word actually consults for interactive drag-resize
- A markdown `---` (thematic break) now produces a real page break instead of just a horizontal line - Pandoc renders it as a VML shape, not a break, so nothing previously converted one into the other
- Install docs: added the missing `git clone` step, clarified that `install.ps1` (admin rights, machine-wide winget installs) must be run by the user rather than Claude, and dropped a stale `python-docx-template` dependency `install.ps1` never actually installed

### Changed
- `lib/dilon_docx_common.py` extracted as the shared Pandoc-conversion/styling helper module used by both compiler skills

> Note: `[2.0.0]` is reused below for an earlier, unrelated release (the MCP-server-to-plugin rework), predating the `[2.0.0]` entry above. Entries are ordered by date, not by version number - see git history for the authoritative record.

## [2.0.0] - 2026-06-30

### Changed
- **BREAKING:** Reworked from an MCP server into a Claude Code Plugin with two Skills
  - `dilon-document-writer` - document stub creation and Dilon markdown styling guidance (replaces `dilon_generate_stub` and the `dilon://styling/markdown` resource)
  - `dilon-document-compiler` - Word document compilation (replaces `dilon_compile_doc`)
  - Distributed via a self-hosted Claude Code plugin marketplace (`.claude-plugin/marketplace.json`) instead of an npm package on GitHub Packages
- Trimmed `install.ps1` to Python/Pandoc/pip-package setup only

### Removed
- **BREAKING:** PlantUML support (`dilon_plantuml` tool, PlantUML style guide, Java/PlantUML install steps)
- The Node.js MCP server and all its scaffolding (`server.js`, `src/`, `bin/`, `scripts/postinstall.js`, `scripts/preuninstall.js`, `package.json`, the `@modelcontextprotocol/sdk` dependency)
- npm packaging and the GitHub Packages publish workflow
- `.dilon-tools-config.json` (no longer needed - skills read bundled files directly)

### Added
- `skills/dilon-document-compiler/scripts/check_deps.py` - preflight dependency check
- `tests/run_tests.py` - direct-invocation test suite replacing the MCP-protocol-based `test-all-features.js`

## [2.2.0] - 2026-08-18

### Added
- `dilon-document-form-compiler` skill (`scripts/generate_dilon_form.py`, `scripts/form_fields.py`, `scripts/check_deps.py`) - compiles the same Dilon-front-matter markdown into a running-header/footer-only Word document (no title page, no signature-approval page, no table of contents), for forms/travelers meant to be printed and filled out by hand
- `@@@FORM_FIELD:FillLine@@@Label@@@END_FORM_FIELD@@@` marker (form compiler only) - a label followed by a right-aligned, underscore-leadered fill-in blank sized to the page's or table cell's true available width
- `lib/dilon_docx_common.py` - Pandoc-conversion/styling helpers shared by both compiler skills, extracted from `generate_dilon_doc.py`
- Body-level `{{field}}` substitution: document body text can now reference any YAML front-matter field (e.g. `{{doc_number}}`, `{{title}}`), resolved via Jinja2 against the same metadata dict that drives the header/footer/signature table/title page
- `include_toc` flag on `markdown_to_docx()`, letting the form compiler skip table-of-contents generation

### Changed
- **BREAKING:** `generate_dilon_doc.py`'s CLI dropped its fourth argument - `python generate_dilon_doc.py <input.md> <output.docx> <base_template>` (was `<signature_template> <content_template>`)
- Header, footer, signature-approval table, and title page are now all generated programmatically via python-docx instead of `docxtpl`/Jinja2 Word-template substitution - fixes a real bug where the signature table's Jinja fields were silently never rendering (`docxtpl.get_docx()` resets to an unrendered template copy when called after `.render()`)
- `TEMPLATE_Word_Signature.docx` renamed to `TEMPLATE_Word_Base.docx` (it no longer carries a signature-specific table); its header/footer content is now built fresh at compile time rather than template-baked, and its top margin increased 1.0in → 1.4in
- Formatting fixes surfaced by review: signature/revision/header tables given explicit grid borders (`Normal Table` style has none) and rebalanced column widths; header table resized to fit within the page's available content width; the doc_number footer line's broken hanging-indent/tab-stop fixed to true left-justification; footer font set to 9pt with separator borders

### Removed
- `docxtpl` (`python-docx-template`) dependency, replaced by direct `jinja2` usage plus plain python-docx calls
- `templates/TEMPLATE_Word_Content.docx` - its title-page content is now hardcoded in `build_title_page()` (`generate_dilon_doc.py`)
- "PRINTED COPIES ARE FOR REFERENCE ONLY." footer line

## [2.1.1] - 2026-07-02

### Fixed
- Two tables placed back-to-back in the source markdown, separated only by a `@@@TABLE_STYLE@@@`/`@@@TABLE_COLUMNS@@@` marker for the second table, were merged by Word into a single visual table on open - deleting the consumed marker paragraph left the two `<w:tbl>` elements directly adjacent in `document.xml` with no separating `<w:p>`. `generate_dilon_doc.py` now empties (rather than removes) a marker paragraph when both its XML neighbors are tables

## [2.1.0] - 2026-07-02

### Added
- `@@@TABLE_COLUMNS:w1,w2,...@@@` marker for `dilon-document-compiler`, letting authors hardcode per-column table widths (inches), stackable with `@@@TABLE_STYLE@@@`. One entry may be `x` to flexibly absorb the page's remaining content width; invalid specs (entry-count mismatch, wrong `x` count, widths that don't fit the page) warn and fall back to Word's default auto-sized width rather than failing compilation.
- Automatic, Word-native section numbering: `Heading 2/3/4` are linked to a shared multilevel list in `TEMPLATE_Word_Signature.docx`, so headings are written as `## Section Name` (no manual "N." prefix) and Word numbers them ("2.", "2.1", "2.1.1") itself.
- Automatic, Word-native figure numbering: caption text now lives in the image's alt-text brackets - `![Description.](path.png){#fig:label}` - with no manually-typed number. `apply_figure_captions()` in `generate_dilon_doc.py` rewrites the resulting caption paragraph into a `Caption`-styled paragraph carrying live `STYLEREF`/`SEQ` fields, chapter-numbered off the nearest Heading 2 (`Figure 2.1 - Description.`). The optional `{#fig:label}` id supports `[text](#fig:label)` figure cross-references, reusing the existing internal-cross-reference link syntax.
- `Captioned Figure` / `Image Caption` paragraph styles in `TEMPLATE_Word_Signature.docx` - detection-only styles that let Pandoc's implicit-figure captions be told apart from an ordinary paragraph that happens to follow a decorative, uncaptioned image (`![]()`), which produces identical paragraph structure otherwise
- `set_update_fields_on_open()` in `generate_dilon_doc.py` - sets `updateFields` in the compiled document's settings so Word recalculates all fields (figure numbers, TOC page numbers) the moment the document opens, instead of showing stale cached values until a manual update
- Test coverage in `tests/run_tests.py`: `test_heading_auto_numbering()`, `test_figure_auto_numbering()`, `test_compile_resolves_relative_image_paths()`

### Changed
- **BREAKING:** Section headings and figure captions must no longer include a manually-typed number - `TEMPLATE_Document.md`, `MARKDOWN_STYLING_GUIDE.md`, and `STYLING_TEST_TEMPLATE.md` are updated to the new convention. Existing documents with manually-numbered headings/captions will show doubled numbers once compiled against the updated template and need their manual numbers stripped

### Fixed
- `dilon-document-compiler`'s `generate_dilon_doc.py` resolved its default signature/content templates against its own `scripts/` directory instead of the sibling `templates/` directory, breaking any invocation with fewer than four explicit arguments
- Removed the `#!/usr/bin/env python3` shebang from all repo Python scripts, since Windows' `py` launcher parses it and can re-dispatch to an unrelated, dependency-less `python3.exe` instead of the real interpreter
- `generate_dilon_doc.py` opened input markdown as `utf-8`, so a leading UTF-8 BOM (written by, e.g., PowerShell's `Set-Content -Encoding UTF8`) made the YAML front-matter regex silently fail to match, dropping all document metadata with no error; now opens with `utf-8-sig`
- A `@@@TABLE_STYLE:...@@@` marker immediately followed by its table (the documented, no-blank-line convention) could get merged by Pandoc into a single garbled text paragraph, since Pandoc's pipe-table parser requires a preceding blank line; the destroyed table's marker text could then also mis-attribute its style to an unrelated adjacent table. `markdown_to_docx()` now inserts a blank line after table-style markers before handing the markdown to Pandoc
- `markdown_to_docx()` resolved relative image paths (e.g. `diagrams/foo.png`) against the compiler's own current working directory instead of the input markdown file's directory, and silently swallowed Pandoc's resource-fetch warnings on success - so images could silently go missing from a compiled document depending on which directory the compiler was invoked from. Now passes `--resource-path` and always prints Pandoc's stderr

### Planned Features
- Extended usage examples

## [1.1.3] - 2026-01-20

### Security
- **Upgraded @modelcontextprotocol/sdk from v0.5.0 to v1.25.3**
  - Fixed DNS rebinding protection vulnerability (GHSA-w48q-cv73-mx4w)
  - Fixed ReDoS (Regular Expression Denial of Service) vulnerability (GHSA-8r9q-7v3j-jr4g)
  - No breaking changes - all tests pass (18 MCP tests + 5 validation tests)
  - npm audit now shows 0 vulnerabilities

### Changed
- Updated package dependencies for security compliance
- Verified all MCP server functionality after SDK upgrade

## [1.1.2] - 2026-01-20

### Fixed
- Fixed Python 3.13 compatibility issue with PyYAML
  - Updated install.ps1 to require PyYAML 6.0 or later
  - Resolved `AttributeError: module 'collections' has no attribute 'Hashable'`
  - PyYAML versions prior to 6.0 are incompatible with Python 3.13+

### Technical Details
- Python 3.13 removed the deprecated `collections.Hashable` (moved to `collections.abc.Hashable`)
- PyYAML 6.0+ includes the fix for Python 3.10+ compatibility
- Installation script now enforces minimum PyYAML version with `pyyaml>=6.0`

## [1.1.1] - 2025-11-24

### Changed
- Updated Word document templates with improved formatting
  - TEMPLATE_Word_Content.docx - Enhanced content formatting
  - TEMPLATE_Word_Signature.docx - Refined signature page layout

## [1.1.0] - 2025-10-20

### Added
- **dilon_generate_stub** - New MCP tool for generating document stubs
  - Creates markdown files from TEMPLATE_Document.md template
  - Customizable YAML front matter (title, author, doc_number, department, etc.)
  - All parameters optional except output_path
  - Default values: revision "00", department/representatives "--"
  - Automatic revision number synchronization with current_revision
  - Validates against duplicate files
- **MCP Resources** - Styling guides now available as MCP resources
  - `dilon://styling/markdown` - Comprehensive markdown styling guide (30,033 chars)
  - `dilon://styling/plantuml` - PlantUML style guide with xUML conventions (22,038 chars)
  - Passively available for Claude to reference when needed
- **Comprehensive Test Suite** - Automated testing infrastructure
  - `tests/test-all-features.js` - 18 MCP integration tests
  - `tests/validate-output.py` - 5 Python validation tests
  - Tests all tools, resources, and output validation
  - 100% test coverage for new features
  - npm test script configured
- **Test Documentation** - `tests/README.md` with complete testing guide

### Changed
- Updated TEMPLATE_Document.md
  - Removed "Notes for Using This Template" section (info now in resources)
  - Removed example sections 1.3, 2, 3, and 4
  - Kept only essential Purpose and Scope sections
  - Changed default revision from "1.0" to "00"
  - Changed default department/representatives to "--"
- Updated tool descriptions to reference styling guide resources
  - `dilon_compile_doc` now reminds to reference markdown styling guide
  - `dilon_plantuml` now reminds to reference PlantUML styling guide
  - `dilon_generate_stub` references markdown styling guide
- Updated MCP server capabilities
  - Added `resources` capability alongside `tools`
  - Registered 3 tools (was 2): dilon_compile_doc, dilon_plantuml, dilon_generate_stub
  - Registered 2 resources: markdown and PlantUML styling guides
- Updated CLAUDE.md with comprehensive documentation of new features

### Technical Details
- Server now implements both `ListResourcesRequestSchema` and `ReadResourceRequestSchema`
- Resource content served directly from docs/ directory
- Test suite uses actual MCP JSON-RPC protocol for integration testing
- Python validation uses python-docx and pyyaml for structural verification
- Added tests/test-output/ to .gitignore

## [1.0.1] - 2025-10-17

### Fixed
- Fixed async import syntax errors in `src/utils.js`
  - Moved `existsSync`, `parse`, and `format` imports to top of file
  - Removed invalid `await import()` calls from non-async functions
  - Fixes "Unexpected reserved word" error when MCP server starts

### Changed
- Changed package scope from `@dilon/claude-tools` to `@dilontechnologies/claude-tools`
  - Package name now matches GitHub organization name
  - Required for successful publishing to GitHub Packages
- Updated all documentation with correct package name
- Updated GitHub Actions workflow with correct scope

## [1.0.0] - 2025-01-17

### Added
- Initial release of Dilon Claude Tools MCP Server
- **dilon_compile_doc** tool for compiling Markdown to formatted Word documents
  - YAML front matter support for metadata
  - Automatic signature page generation
  - Revision history table creation
  - Table of contents generation
  - Regulatory-compliant formatting (ISO 62304, FDA)
- **dilon_plantuml** tool for generating diagrams from PlantUML files
  - PNG, SVG, and PDF output formats
  - Integration with Dilon PlantUML Style Guide
- Embedded Dilon Document Compiler (Python-based)
  - `generate_dilon_doc.py` script
  - Word templates (signature, content)
  - Markdown styling guide
- PlantUML style guide for company diagram standards
- Comprehensive documentation
  - Setup and usage README
  - Markdown styling reference
  - PlantUML diagram standards
  - Document template
- Automated installation script (`install.ps1`)
  - Auto-detection of dependencies
  - Auto-installation via winget (Python, Pandoc, Java, Plant
  - Python package installation
  - Node.js package installation
  - Configuration file creation
  - MCP server registration with Claude Code
  - PowerShell command installation (Compile-DilonDoc, dilonc alias)
- Configuration management system
  - `.dilon-tools-config.json` for user settings
  - Path management for Python, Pandoc, PlantUML
  - Validation of tool paths
- Test files and examples
  - Styling test templates
  - Test diagrams

### Technical Details
- Node.js MCP server using @modelcontextprotocol/sdk v0.5.0
- ES modules (type: "module")
- Windows-first design with PowerShell integration
- Self-contained repository (no external Nav3 dependency)
- Organized structure:
  - `/src` - MCP server source code
  - `/tools` - Embedded tools (Dilon Document Compiler)
  - `/docs` - Documentation and templates
  - `/tests` - Test files
  - `/examples` - Usage examples (future)

### Infrastructure
- Git repository initialized
- GitHub remote configured: https://github.com/dilontechnologies/dilon-claude-tools.git
- .gitignore configured for Node.js and user configs
- Package.json with proper metadata

---

**Note:** This changelog tracks changes to the MCP server and tooling infrastructure. For changes to individual tools (e.g., Dilon Document Compiler), see the respective tool documentation in `tools/`.
