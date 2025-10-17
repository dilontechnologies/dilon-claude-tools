# Dilon Document Compiler

Python-based document generation system for creating regulatory-compliant Word documents from Markdown source files with YAML metadata.

**Part of:** [Dilon Claude Tools MCP Server](../../README.md)

## Overview

This tool generates properly formatted Word documents for Dilon Technologies by:
1. Parsing Markdown files with YAML front matter
2. Rendering Word templates with Jinja2 variables
3. Converting Markdown content to Word format via Pandoc
4. Merging all components into a final document

### Integration Options

This compiler can be used in three ways:

1. **Via Claude Code MCP Server** (Recommended)
   - Automatically available as `dilon_compile_doc` tool in Claude Code
   - No manual invocation needed - Claude handles it automatically
   - See [main README](../../README.md) for setup

2. **Via PowerShell Command**
   - Use `Compile-DilonDoc` or `dilonc` commands from any directory
   - Installed automatically by the MCP server installer
   - See "PowerShell Usage" section below

3. **Via Python Directly**
   - Direct script invocation for custom workflows
   - See "Python Usage" section below

## Features

- **YAML Metadata Support**: Extract document metadata (title, author, revision history, etc.) from Markdown front matter
- **Jinja2 Templating**: Populate Word templates with dynamic variables
- **Revision History Tables**: Automatically generate formatted revision tables with:
  - Title row ("REVISION HISTORY")
  - Gray header row with columns: REV #, DESCRIPTION, ECO #, DATE
  - Dynamic data rows from YAML metadata
  - Custom column widths (narrow REV #, wide DESCRIPTION)
  - Centered alignment
- **Table of Contents**: Automatically generated from document headings
  - Includes all heading levels (H1-H6)
  - Formatted with page break after TOC
  - **Important**: Major section headings should always use H2 for proper TOC formatting
- **Markdown Conversion**: Convert Markdown body to Word using Pandoc
- **Document Composition**: Merge multiple document parts in sequence:
  - Part A: Signature page with metadata
  - Part B: Revision history table
  - Part C: Title page and content template
  - Part D: Table of contents and markdown content

## Requirements

**Note:** If using the MCP server, all requirements are installed automatically by `install.ps1`. Manual installation is only needed for standalone use.

### Python Packages
```bash
pip install python-docx python-docx-template docxcompose pyyaml
```

### External Tools
- **Pandoc**: Required for Markdown to Word conversion
  - Download: https://pandoc.org/installing.html
  - Must be accessible in system PATH

## Installation

### Via MCP Server (Recommended)

The Dilon Claude Tools MCP Server installer handles everything automatically:

```powershell
cd C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
.\install.ps1
```

This installs:
- Python and required packages
- Pandoc
- MCP server integration
- PowerShell commands (`Compile-DilonDoc`, `dilonc`)

See [main README](../../README.md) for details.

### Standalone Installation

For standalone use without the MCP server:

1. Install Python packages:
   ```powershell
   pip install python-docx python-docx-template docxcompose pyyaml
   ```

2. Install Pandoc from https://pandoc.org/installing.html

3. Use Python directly (see "Python Usage" below)

## Usage

### Via Claude Code (MCP Server)

Once the MCP server is installed, simply ask Claude in conversation:

```
User: "Compile Documentation/Requirements.md to a Word document"

Claude: *automatically uses dilon_compile_doc tool*
        ✅ Document compiled successfully!
```

No manual commands needed - Claude handles invocation automatically.

### PowerShell Usage
```powershell
# Auto-generate output filename (MyDocument.docx)
Compile-DilonDoc MyDocument.md

# Specify output filename
Compile-DilonDoc MyDocument.md Output.docx

# Short alias
dilonc MyDocument.md Output.docx
```

The `Compile-DilonDoc` function and `dilonc` alias are installed automatically by the MCP server installer.

### Python Usage (Direct)
```bash
python generate_dilon_doc.py <input.md> <output.docx>
```

### With Custom Templates
```bash
python generate_dilon_doc.py <input.md> <output.docx> <signature_template.docx> <content_template.docx>
```

### Examples
```powershell
# PowerShell (from any directory)
dilonc MAP-00001_Requirements.md

# Python (must be in script directory or use full path)
python generate_dilon_doc.py MAP-00001_Requirements.md MAP-00001_Requirements.docx
```

## Input File Format

### Markdown with YAML Front Matter

```markdown
---
title: "MAP-00001: Manufacturing Test Tool Requirements"
author: "Development Team"
department: "Engineering"
doc_number: "DD_SRS_00002"
current_revision: "1.1"
regulatory_rep: "Shannon Smith"
quality_rep: "Kevin Johnson"
department_head: "Josh Williams"
revisions:
  - number: "1.0"
    description: "Initial requirements specification"
    eco_number: "ECO-TBD"
    eco_date: "2025-09-25"
  - number: "1.1"
    description: "Updated pass/fail criteria"
    eco_number: "ECO-TBD"
    eco_date: "2025-10-02"
---

## Document Content

Your Markdown content goes here...

### Sections

- Use standard Markdown syntax
- Headings, lists, tables, code blocks all supported
- Converted to Word format automatically
```

## Template Structure

### Part A: Signature Template (TEMPLATE_Word_Signature.docx)
**Purpose**: Master document with company formatting and signature tables

**Contains**:
- All style definitions (establishes master styles for entire document)
- Signature approval table
- Document properties section
- Master Document notice
- Effectivity and Location section
- Approval, Release and Change History section

**Jinja2 Variables**:
- `{{title}}`
- `{{author}}`
- `{{department}}`
- `{{doc_number}}`
- `{{current_revision}}`
- `{{regulatory_rep}}`
- `{{quality_rep}}`
- `{{department_head}}`

### Part B: Revision Table (Generated Programmatically)
**Purpose**: Dynamic revision history table

**Generated by**: `create_revision_table()` function in script

**Format**:
- Title row: "REVISION HISTORY" (gray background, merged cells)
- Header row: REV # | DESCRIPTION | ECO # | DATE (gray, bold, centered)
- Data rows from `revisions` array in YAML

**Column Widths**:
- REV #: 0.6 inches
- DESCRIPTION: 3.5 inches
- ECO #: 1.0 inch
- DATE: 1.0 inch

### Part C: Content Template (TEMPLATE_Word_Content.docx)
**Purpose**: Title page and content wrapper

**Contains**:
- Page break (starts new page after revision table)
- Title section
- Author/Revised by table
- Any additional front matter after revision table

**Jinja2 Variables**:
- `{{title}}`
- `{{author}}`

## Document Generation Workflow

```
Input Markdown File
        |
        v
┌───────────────────┐
│ Extract YAML      │
│ Extract Markdown  │
└────────┬──────────┘
         |
         ├─────────────────────────────────┐
         v                                 v
┌─────────────────┐              ┌─────────────────┐
│ Part A          │              │ Part B          │
│ Render Sig Page │              │ Generate Table  │
│ with Metadata   │              │ from Revisions  │
└────────┬────────┘              └────────┬────────┘
         |                                |
         |        ┌────────────────┐      |
         |        │ Part C         │      |
         |        │ Render Title   │      |
         |        │ with Metadata  │      |
         |        └────────┬───────┘      |
         |                 |              |
         |        ┌────────────────┐      |
         |        │ Part D         │      |
         |        │ Convert MD     │      |
         |        │ via Pandoc     │      |
         |        └────────┬───────┘      |
         |                 |              |
         v                 v              v
┌───────────────────────────────────────────┐
│         docxcompose Merger                │
│      A → B → C → D                        │
└────────────────┬──────────────────────────┘
                 v
         Final Document.docx
```

## Technical Details

### Libraries Used

1. **PyYAML**: Parses YAML front matter from Markdown files
2. **python-docx-template (docxtpl)**: Jinja2 templating for Word documents
3. **python-docx**: Low-level Word document manipulation (table creation, formatting)
4. **docxcompose**: Merges multiple Word documents sequentially
5. **Pandoc** (external): Converts Markdown to Word format

### Style Inheritance

The **first document** (Part A - Signature Template) establishes the master styles for the entire document. All subsequent parts (B, C, D) inherit these styles. This ensures consistent formatting throughout the final document.

### Why Split Templates?

Originally attempted to use a single template with placeholder insertion, but:
- Jinja2 subdocument features had limitations
- Placeholder text insertion was unreliable
- docxcompose excels at sequential appending, not mid-document insertion

Split template approach leverages docxcompose's strength: appending complete documents in sequence.

## Customization

### Modifying Revision Table Format

Edit the `create_revision_table()` function in `generate_dilon_doc.py`:

**Change column widths**:
```python
table.columns[0].width = Inches(0.6)   # REV #
table.columns[1].width = Inches(3.5)   # DESCRIPTION
table.columns[2].width = Inches(1.0)   # ECO #
table.columns[3].width = Inches(1.0)   # DATE
```

**Change title text**:
```python
title_cell.text = "REVISION HISTORY"  # Change this
```

**Change header background color**:
```python
shading_elm.set(qn('w:fill'), 'C0C0C0')  # Gray (hex color)
```

### Adding New Template Variables

1. Add variable to YAML front matter in Markdown file
2. Add `{{variable_name}}` to template(s) where needed
3. No code changes required - metadata dictionary automatically includes all YAML fields

### Creating New Document Types

1. Create new signature template (Part A) with desired formatting
2. Create new content template (Part C) for title page layout
3. Run script with custom template paths:
```bash
python generate_dilon_doc.py input.md output.docx custom_sig.docx custom_content.docx
```

## Troubleshooting

### "Template not found" Error
- Ensure templates are in correct location (same directory as script by default)
- Use absolute paths if templates are elsewhere
- Check file names match exactly (case-sensitive on some systems)

### "Pandoc command not found"
- Install Pandoc: https://pandoc.org/installing.html
- Ensure Pandoc is in system PATH
- Test: `pandoc --version` in terminal

### Document Corruption / "Word cannot open file"
- Usually caused by permission issues (file open in Word)
- Close all Word documents before running script
- Check output path is writable

### Revision Table Not Appearing
- Verify `revisions` array exists in YAML front matter
- Check YAML syntax (proper indentation, list format)
- Ensure revision objects have required fields: `number`, `description`, `eco_number`, `eco_date`

### Formatting Not Preserved
- Ensure Part A (signature template) contains all style definitions
- Check that Part C uses same style names as Part A
- Verify templates use Word styles, not direct formatting

## File Structure

**Within MCP Server Repository:**

```
dilon-claude-tools/
├── tools/Dilon_Document_Compiler/
│   ├── generate_dilon_doc.py          # Main Python script
│   ├── TEMPLATE_Word_Signature.docx   # Part A template (signature page)
│   ├── TEMPLATE_Word_Content.docx     # Part C template (title page)
│   └── README.md                      # This file
├── docs/
│   ├── TEMPLATE_Document.md           # Markdown template with YAML fields
│   └── MARKDOWN_STYLING_GUIDE.md      # Styling reference
└── install.ps1                        # Main installer (installs everything)
```

## Creating New Documents

### Quick Start

1. **Copy the markdown template**:
   ```bash
   # Template is now in docs/ directory
   cp ../../docs/TEMPLATE_Document.md Your_Document_Name.md
   ```

2. **Edit the YAML front matter**:
   - Update `title`, `author`, `department`, `doc_number`, etc.
   - Modify revision history as needed
   - Keep the `---` delimiters intact

3. **Write your content**:
   - Use standard Markdown syntax
   - **Use H2 (`##`) for major section headings** (required for proper TOC formatting)
   - Use H3-H6 for subsections as needed
   - Replace placeholder sections with your content
   - Delete the "Notes for Using This Template" section

4. **Generate Word document**:
   ```bash
   python generate_dilon_doc.py Your_Document_Name.md Your_Document_Name.docx
   ```

### Markdown Template Fields

The `TEMPLATE_Document.md` includes all required YAML fields:
- **title**: Full document title
- **author**: Primary author or team name
- **department**: Usually "Engineering"
- **doc_number**: Dilon document number (DD_XXX_XXXXX)
- **current_revision**: Current revision number
- **regulatory_rep**: Regulatory representative name
- **quality_rep**: Quality representative name
- **department_head**: Department head name
- **revisions**: Array of revision history entries
  - `number`: Revision number
  - `description`: Description of changes
  - `eco_number`: ECO tracking number
  - `eco_date`: Date of revision

## Version History

- **v1.0** (2025-10-02): Initial release with split template architecture
  - Signature page with metadata variables
  - Programmatic revision table generation
  - Title page template
  - Markdown content conversion
  - Sequential document merging

## Related Documentation

- **[Main MCP Server README](../../README.md)** - Setup and usage of the complete MCP server
- **[Markdown Styling Guide](../../docs/MARKDOWN_STYLING_GUIDE.md)** - Formatting reference
- **[Document Template](../../docs/TEMPLATE_Document.md)** - Template for new documents
- **[PlantUML Style Guide](../../docs/PlantUML_Style_Guide.md)** - Diagram standards

## License

Internal use only - Dilon Technologies LLC

## Support

For questions or issues:
- Check the [main README troubleshooting section](../../README.md#troubleshooting)
- Review the [Markdown Styling Guide](../../docs/MARKDOWN_STYLING_GUIDE.md)
- Contact the Engineering Department
