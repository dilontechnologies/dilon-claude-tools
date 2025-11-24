# Dilon Claude Tools - Codebase Knowledge

## Package Overview

This is an **npm (Node.js) package** that implements a **Model Context Protocol (MCP) server** for Claude Code. It's designed for Windows environments and provides tools for regulatory-compliant technical documentation workflows at Dilon Technologies.

**Package Details:**
- Name: `@dilontechnologies/claude-tools`
- Version: 1.1.1
- Published to: GitHub Packages (private registry)
- License: UNLICENSED (internal use only)
- Node.js: >= 18.0.0

**Publishing Workflow:**
- **Automatic Publishing:** Package is automatically published to GitHub Packages via GitHub Actions workflow
- **Trigger:** Pushing a git tag matching `v*` pattern (e.g., `v1.1.1`) triggers the publish workflow
- **Process:** Create version tag → push to origin → GitHub Actions automatically publishes
- **Manual Publishing:** Can also be published manually via `npm publish` if needed

## Existing Tools/Features

The MCP server currently provides **three main tools** to Claude Code:

### Tool 1: `dilon_generate_stub`
**Purpose:** Generates new Dilon document stubs from the template with customizable YAML front matter

**Capabilities:**
- Creates markdown files from the TEMPLATE_Document.md template
- Customizable YAML front matter (title, author, doc_number, etc.)
- All parameters optional except output_path
- Default values: revision "00", department/reps "--"
- Includes Purpose and Scope sections ready for content

**Implementation:** `src/tools/generate-stub.js`

**Usage Example:**
```javascript
{
  "output_path": "path/to/new_document.md",
  "title": "Software Requirements Specification",
  "author": "Engineering Team",
  "doc_number": "DD_SWE_12345"
}
```

### Tool 2: `dilon_compile_doc`
**Purpose:** Compiles Markdown files with YAML front matter into formatted Word documents

**Capabilities:**
- Parses YAML metadata (title, author, revisions, approvers, etc.)
- Generates signature pages automatically
- Creates revision history tables dynamically
- Converts Markdown to Word using Pandoc
- Assembles multi-part documents (signature page + revision table + content + TOC)
- Supports custom Word templates
- Regulatory-compliant formatting (ISO 62304, FDA submission ready)

**Implementation:** `src/tools/dilon-compiler.js`

**Note:** Tool description references the `dilon://styling/markdown` resource for styling guidelines.

### Tool 3: `dilon_plantuml`
**Purpose:** Generates diagrams from PlantUML files using Dilon styling conventions

**Capabilities:**
- Supports multiple output formats (PNG, SVG, PDF)
- Follows company PlantUML style guide standards
- Handles both `plantuml` command and `java -jar` fallback
- Provides style guide references

**Implementation:** `src/tools/plantuml.js`

**Note:** Tool description references the `dilon://styling/plantuml` resource for styling guidelines.

## MCP Resources

The MCP server provides **two resources** that expose styling guides:

### Resource 1: `dilon://styling/markdown`
**Purpose:** Comprehensive Dilon markdown styling guide

**Content:** Complete reference from `docs/MARKDOWN_STYLING_GUIDE.md`

**Covers:**
- YAML front matter requirements
- Heading conventions and numbering
- Table formatting (pipe tables, grid tables, custom styles)
- Figure and image handling
- Lists, code blocks, links
- Custom paragraph styles with `@@@STYLE@@@` markers
- Regulatory compliance formatting

**Usage:** Claude can reference this resource when working with markdown documents or using the `dilon_compile_doc` tool.

### Resource 2: `dilon://styling/plantuml`
**Purpose:** Dilon PlantUML style guide for diagram generation

**Content:** Complete reference from `docs/PlantUML_Style_Guide.md`

**Covers:**
- xUML/Executable UML conventions
- Class diagram standards
- State machine diagrams
- Identifier notation ({I}, {I2}, {R#})
- Relationship types and verb phrases
- Multiplicity notation
- File naming conventions

**Usage:** Claude can reference this resource when creating PlantUML diagrams or using the `dilon_plantuml` tool.

## Project Structure

```
dilon-claude-tools/
├── server.js                          # Main MCP server entry point
├── package.json                       # Node package manifest
├── .dilon-tools-config.example.json   # Configuration template
│
├── bin/
│   └── dilon-tools.js                 # CLI utility (version, info, paths)
│
├── scripts/
│   ├── postinstall.js                 # Auto-registers with Claude Desktop
│   └── preuninstall.js                # Cleanup on uninstall
│
├── src/
│   ├── config.js                      # Config loader & path manager
│   ├── utils.js                       # Execution helpers (Python, PowerShell)
│   └── tools/
│       ├── generate-stub.js           # Document stub generator tool handler
│       ├── dilon-compiler.js          # Document compiler tool handler
│       └── plantuml.js                # PlantUML tool handler
│
├── tools/
│   └── Dilon_Document_Compiler/
│       ├── generate_dilon_doc.py      # Python document generator
│       ├── TEMPLATE_Word_Signature.docx
│       ├── TEMPLATE_Word_Content.docx
│       └── README.md
│
├── docs/
│   ├── MARKDOWN_STYLING_GUIDE.md      # Complete markdown reference
│   ├── PlantUML_Style_Guide.md        # Diagram standards
│   └── TEMPLATE_Document.md           # Document template
│
├── tests/
│   └── STYLING_TEST_TEMPLATE.md
│
└── examples/
```

## Document Generation Features (Templates)

The package includes a sophisticated multi-part document assembly system:

### Template System Components

**Part A: Signature Template** (`TEMPLATE_Word_Signature.docx`)
- Master document with style definitions
- Signature approval table with Jinja2 variables
- Document properties section
- Variables: title, author, department, doc_number, current_revision, regulatory_rep, quality_rep, department_head

**Part B: Revision Table** (Generated programmatically)
- Dynamic revision history table created from YAML metadata
- Formatted with custom column widths, gray headers, centered text

**Part C: Content Template** (`TEMPLATE_Word_Content.docx`)
- Title page and content wrapper
- Author/revision information

**Part D: Markdown Content** (Converted by Pandoc)
- Full markdown to Word conversion with TOC generation

### Markdown Template
`docs/TEMPLATE_Document.md` provides a starter template with:
- Complete YAML front matter structure
- Section templates
- Usage instructions

## MCP Server Implementation

**Fully implemented MCP server** using the official MCP SDK:

**Architecture:**
- Uses `@modelcontextprotocol/sdk` (version 0.5.0)
- Implements stdio transport for Claude Desktop integration
- Registers three tools (dilon_generate_stub, dilon_compile_doc, dilon_plantuml)
- Exposes two resources (markdown and PlantUML styling guides)
- Validates configuration and tool paths on startup

**Key Files:**
- `server.js` - Main MCP server with request handlers
- `src/config.js` - Configuration management and validation
- `src/utils.js` - Command execution utilities
- Tool handlers in `src/tools/`

**Installation Integration:**
- `scripts/postinstall.js` - Automatically registers server with Claude Desktop config
- `scripts/preuninstall.js` - Cleanup on package removal
- Updates `%APPDATA%\Claude\claude_desktop_config.json` automatically

## Styling Guides

### Markdown Styling Guide
**File:** `docs/MARKDOWN_STYLING_GUIDE.md` (995 lines)

**Covers:**
- YAML front matter requirements
- Heading conventions and numbering
- Table formatting (pipe tables and grid tables)
- Custom table styles (DilonTable_List, DilonTable_Chart)
- Figure and image handling
- Lists (ordered, unordered, definition)
- Code blocks and inline code
- Links and cross-references
- Notes and callouts
- Custom paragraph styles with `@@@STYLE@@@` markers
- Footnote formatting
- Complete style reference table

**Key Features:**
- Pandoc-flavored Markdown
- Word style inheritance system
- Custom table style markers
- Multi-line paragraph styling
- Regulatory compliance focus

### PlantUML Style Guide
**File:** `docs/PlantUML_Style_Guide.md` (852 lines)

**Covers:**
- General conventions (theme, layout, formatting)
- Class diagrams (xUML/Executable UML conventions)
- State machine diagrams
- Domain diagrams
- Class identification and stereotypes
- Attribute and operation formatting
- Identifiers (class keys) and referential attributes
- Relationship types with verb phrases
- Multiplicity notation
- Note placement and formatting
- File naming conventions
- Complete examples

**Key Features:**
- Executable UML (xUML) methodology
- Class numbering and abbreviations
- Identifier notation ({I}, {I2}, etc.)
- Referential attribute notation ({R#})
- Verb phrase relationships
- State machine event naming
- Layout management strategies

## Key Architectural Patterns

1. **Tool Modularity:** Each tool is self-contained with its own definition and execute function
2. **Configuration Management:** Centralized config with validation and path resolution
3. **Utility Functions:** Reusable command execution (Python, PowerShell)
4. **Path Resolution:** Handles both absolute and relative paths
5. **Error Handling:** Comprehensive validation with user-friendly error messages
6. **Template Inheritance:** Word styles cascade from master template
7. **State Machine Processing:** Markdown markers processed via state machines

## Dependencies

**Runtime:**
- Node.js >= 18.0.0
- Python >= 3.8 (for document compiler)
- Pandoc (for markdown conversion)
- Java (for PlantUML)
- PlantUML jar

**Node Packages:**
- @modelcontextprotocol/sdk (MCP integration)

**Python Packages:**
- python-docx, python-docx-template, docxcompose, pyyaml

## Design Philosophy

This is a production-ready MCP server designed specifically for regulatory-compliant technical documentation workflows. The package is:
- Well-documented with comprehensive style guides
- Modular with clear separation of concerns
- Designed for maintainability and extensibility
- Focused on consistency across documentation
- Compliant with regulatory standards (ISO 62304, FDA)
