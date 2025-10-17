# Changelog

All notable changes to the Dilon Claude Tools MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
