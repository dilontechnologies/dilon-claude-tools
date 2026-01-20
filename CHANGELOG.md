# Changelog

All notable changes to the Dilon Claude Tools MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

### Planned Features
- Additional MCP tools as needed
- Extended usage examples
- Automated testing framework
- CI/CD pipeline for releases
- Cross-platform support (macOS, Linux)

---

**Note:** This changelog tracks changes to the MCP server and tooling infrastructure. For changes to individual tools (e.g., Dilon Document Compiler), see the respective tool documentation in `tools/`.
