# Dilon Claude Tools

**MCP Server for Dilon Technologies automation tools**

This repository provides a Model Context Protocol (MCP) server that exposes Dilon Technologies' documentation and diagram generation tools to Claude Code, enabling seamless integration of company-specific workflows directly into AI-assisted development.

## 🚀 Features

### Available Tools

- **`dilon_compile_doc`** - Compile Markdown files with YAML front matter into formatted Dilon Word documents
  - Automatic signature pages with metadata
  - Revision history tables
  - Table of contents generation
  - Regulatory-compliant formatting (ISO 62304, FDA submission ready)

- **`dilon_plantuml`** - Generate diagrams from PlantUML files using Dilon styling conventions
  - Supports PNG, SVG, and PDF output formats
  - Follows Dilon PlantUML Style Guide standards
  - Integrated with company diagram standards

## 📋 Prerequisites

The installation script will automatically install missing dependencies, but you can also install them manually:

- **Node.js** (>= 18.0.0) - Required for MCP server
- **Python** (>= 3.8) - Required for document compiler
- **Pandoc** - Required for Markdown → Word conversion
- **Java** - Required for PlantUML diagram generation
- **PlantUML** - Diagram generation tool

## 🔧 Installation

### Automatic Installation (Recommended)

1. **Clone the repository:**
   ```powershell
   cd C:\Users\YourUsername\Local_Documents\Local_Repos
   git clone https://github.com/dilontechnologies/dilon-claude-tools.git
   cd dilon-claude-tools
   ```

2. **Run the installer (as Administrator):**
   ```powershell
   .\install.ps1
   ```

   The installer will:
   - ✅ Check for required dependencies
   - ✅ Auto-install missing dependencies (Python, Pandoc, Java, PlantUML)
   - ✅ Install Python packages (python-docx, pyyaml, etc.)
   - ✅ Install Node.js packages (MCP SDK)
   - ✅ Create configuration file
   - ✅ Register MCP server with Claude Code

3. **Restart Claude Code** to load the new tools

### Manual Installation

If you prefer to install dependencies manually:

```powershell
# Install dependencies
winget install Python.Python.3.11
winget install JohnMacFarlane.Pandoc
winget install EclipseAdoptium.Temurin.21.JRE

# Install Python packages
pip install python-docx python-docx-template docxcompose pyyaml

# Install Node.js packages
npm install

# Create configuration
copy .dilon-tools-config.example.json .dilon-tools-config.json
# Edit .dilon-tools-config.json with your paths

# Register with Claude Code manually (edit claude_desktop_config.json)
```

## 📖 Usage

Once installed, the tools are available directly in Claude Code conversations:

### Compiling Documents

**Example conversation:**
```
User: "Compile Documentation/Requirements.md to a Word document"

Claude: *uses dilon_compile_doc tool*
        ✅ Document compiled successfully!
        📄 Input:  Documentation/Requirements.md
        📦 Output: Documentation/Requirements.docx
```

**The tool handles:**
- YAML front matter extraction (title, author, revisions, etc.)
- Signature page generation
- Revision history table creation
- Markdown → Word conversion with TOC
- Proper Dilon formatting and styling

### Generating Diagrams

**Example conversation:**
```
User: "Generate a PNG diagram from design/state_machine.puml"

Claude: *uses dilon_plantuml tool*
        ✅ Diagram generated successfully!
        📄 Input:  design/state_machine.puml
        📦 Output: design/state_machine.png
        🎨 Format: PNG
```

**Supported formats:**
- PNG (default)
- SVG (vector graphics)
- PDF (printable)

## 📚 Documentation

### Styling Guides

- **[Markdown Styling Guide](docs/MARKDOWN_STYLING_GUIDE.md)** - Complete reference for formatting Dilon documents
- **[PlantUML Style Guide](docs/PlantUML_Style_Guide.md)** - Standards for class diagrams, state machines, and domain diagrams

### Templates

- **[Document Template](docs/TEMPLATE_Document.md)** - Template for creating new Dilon documents with proper YAML front matter

### Tool Documentation

- **Dilon Document Compiler** - `tools/Dilon_Document_Compiler/README.md`
- **PlantUML Integration** - See PlantUML Style Guide

## 🏗️ Repository Structure

```
dilon-claude-tools/
├── README.md                       # This file
├── CHANGELOG.md                    # Version history
├── package.json                    # Node.js package manifest
├── server.js                       # Main MCP server
├── install.ps1                     # Installation script
├── .dilon-tools-config.json        # User configuration (created by installer)
├── src/
│   ├── config.js                   # Configuration manager
│   ├── utils.js                    # Utility functions
│   └── tools/
│       ├── dilon-compiler.js       # Document compiler tool handler
│       └── plantuml.js             # PlantUML tool handler
├── tools/
│   └── Dilon_Document_Compiler/    # Embedded document compiler
│       ├── generate_dilon_doc.py   # Python compilation script
│       ├── TEMPLATE_Word_*.docx    # Word templates
│       └── README.md               # Compiler documentation
├── docs/
│   ├── MARKDOWN_STYLING_GUIDE.md   # Markdown formatting reference
│   ├── PlantUML_Style_Guide.md     # PlantUML diagram standards
│   └── TEMPLATE_Document.md        # New document template
├── examples/
│   └── (usage examples)
└── tests/
    ├── STYLING_TEST_TEMPLATE.md    # Test file for styling
    └── diagrams/                   # Test diagrams
```

## ⚙️ Configuration

Configuration is stored in `.dilon-tools-config.json`:

```json
{
  "pythonPath": "python",
  "plantUmlPath": "C:\\Program Files\\PlantUML",
  "pandocPath": "pandoc"
}
```

**Configuration fields:**
- `pythonPath` - Path to Python executable (default: `python`)
- `plantUmlPath` - Directory containing `plantuml.jar`
- `pandocPath` - Path to Pandoc executable (default: `pandoc`)

## 🔍 Troubleshooting

### MCP Server Not Showing in Claude Code

1. Check that Claude Code config was updated:
   ```powershell
   cat $env:APPDATA\Claude\claude_desktop_config.json
   ```

2. Verify the server entry exists:
   ```json
   {
     "mcpServers": {
       "dilon-claude-tools": {
         "command": "node",
         "args": ["C:\\...\\dilon-claude-tools\\server.js"]
       }
     }
   }
   ```

3. Restart Claude Code completely

### Tools Not Found

Run the configuration validator:
```powershell
node server.js
```

Look for error messages about missing tools or dependencies.

### Python Package Errors

Reinstall Python dependencies:
```powershell
pip install --upgrade python-docx python-docx-template docxcompose pyyaml
```

### PlantUML Not Working

1. Verify Java is installed:
   ```powershell
   java -version
   ```

2. Check PlantUML jar exists:
   ```powershell
   Test-Path "C:\Program Files\PlantUML\plantuml.jar"
   ```

3. Test PlantUML manually:
   ```powershell
   java -jar "C:\Program Files\PlantUML\plantuml.jar" -version
   ```

## 🔄 Updating

To update to the latest version:

```powershell
cd C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
git pull
npm install
```

Restart Claude Code after updating.

## 🤝 Contributing

This repository is maintained by Dilon Technologies for internal use.

**For team members:**
1. Make changes in a feature branch
2. Test thoroughly using the test files in `tests/`
3. Update `CHANGELOG.md` with your changes
4. Create a pull request for review

## 📄 License

Internal use only - Dilon Technologies LLC

## 🆘 Support

For questions or issues:
- Check the troubleshooting section above
- Review the styling guides in `docs/`
- Contact the Engineering Department

## 🔗 Related Projects

- **Navigator 3.0** - Medical device gamma probe project
- **MAP Desktop Application** - Manufacturing Assistance Programs

---

**Version:** 1.0.0
**Last Updated:** 2025-01-17
**Maintained by:** Dilon Technologies Engineering Team
