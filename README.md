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

- **Node.js** (>= 18.0.0) - Required for MCP server
- **npm** - Node package manager (included with Node.js)
- **GitHub Personal Access Token** (for installation from GitHub Packages)

Dependencies (automatically installed by the package):
- **Python** (>= 3.8) - Required for document compiler
- **Pandoc** - Required for Markdown → Word conversion
- **Java** - Required for PlantUML diagram generation
- **PlantUML** - Diagram generation tool

## 🔧 Installation

### NPM Installation (Recommended)

**For Dilon Technologies team members:**

1. **Create GitHub Personal Access Token** (one-time setup)
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scopes: `read:packages`
   - Copy the token

2. **Configure npm to use GitHub Packages:**
   ```powershell
   npm config set @dilon:registry https://npm.pkg.github.com
   npm config set //npm.pkg.github.com/:_authToken YOUR_TOKEN_HERE
   ```

3. **Install the package globally:**
   ```powershell
   npm install -g @dilon/claude-tools
   ```

   The postinstall script will automatically:
   - ✅ Register MCP server with Claude Desktop
   - ✅ Create default configuration file
   - ✅ Check for missing dependencies (Python, Pandoc, Java, PlantUML)
   - ✅ Install Python packages (python-docx, pyyaml, etc.)

4. **Install missing dependencies** (if prompted):
   ```powershell
   npm explore @dilon/claude-tools -- npm run install-deps
   ```

   Or install manually using the dependency installer.

5. **Restart Claude Desktop** to load the new tools

6. **Verify installation:**
   ```powershell
   dilon-tools info
   ```

### Manual Installation (Alternative)

If you need to install from source or make local modifications:

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
   - ✅ Register MCP server with Claude Desktop
   - ✅ Install PowerShell commands (Compile-DilonDoc, dilonc)

3. **Restart Claude Desktop** to load the new tools

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

## 🖥️ CLI Commands

The `dilon-tools` CLI is installed globally and provides useful commands:

```powershell
# Show version
dilon-tools version

# Show package information and available tools
dilon-tools info

# Show installation directory
dilon-tools path

# Show MCP server path
dilon-tools server-path

# Show configuration file paths
dilon-tools config

# Show help
dilon-tools help
```

## 📚 Documentation

### Styling Guides

- **[Markdown Styling Guide](docs/MARKDOWN_STYLING_GUIDE.md)** - Complete reference for formatting Dilon documents
- **[PlantUML Style Guide](docs/PlantUML_Style_Guide.md)** - Standards for class diagrams, state machines, and domain diagrams

### Templates

- **[Document Template](docs/TEMPLATE_Document.md)** - Template for creating new Dilon documents with proper YAML front matter

### Tool Documentation

- **Dilon Document Compiler** - `tools/Dilon_Document_Compiler/README.md`
- **PlantUML Integration** - See PlantUML Style Guide

### Publishing

- **[Publishing Guide](PUBLISHING.md)** - Instructions for package maintainers to publish updates to GitHub Packages

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

### NPM Installation

To update to the latest version:

```powershell
npm update -g @dilon/claude-tools
```

Restart Claude Desktop after updating.

### Manual Installation

For manual installations:

```powershell
cd C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
git pull
npm install
```

Restart Claude Desktop after updating.

## 🗑️ Uninstallation

### NPM Installation

```powershell
npm uninstall -g @dilon/claude-tools
```

The preuninstall script will automatically:
- ✅ Remove MCP server registration from Claude Desktop config
- ✅ Clean up package files

### Manual Installation

1. Remove the MCP server entry from Claude Desktop config:
   - Open `%APPDATA%\Claude\claude_desktop_config.json`
   - Remove the `dilon-claude-tools` entry from `mcpServers`

2. Delete the repository folder:
   ```powershell
   rm -r C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
   ```

Restart Claude Desktop after uninstallation.

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
