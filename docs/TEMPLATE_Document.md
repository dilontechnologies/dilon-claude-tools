---
title: "Document Title"
author: "Author Name"
department: "Engineering"
doc_number: "DD_XXX_XXXXX"
current_revision: "1.0"
regulatory_rep: "Shannon Smith"
quality_rep: "Kevin Johnson"
department_head: "Josh Williams"
revisions:
  - number: "1.0"
    description: "Initial release"
    eco_number: "ECO-TBD"
    eco_date: "YYYY-MM-DD"
---

## 1. Purpose and Scope

### 1.1 Purpose
[Describe the purpose of this document]

### 1.2 Scope
[Describe the scope of this document]

### 1.3 Medical Device Context (if applicable)
- **Device Classification**: ISO 62304 Class B Medical Device
- **Regulatory**: FDA submission requirements
- **Safety-Critical**: Real-time gamma ray detection for surgical navigation

## 2. Section Title

### 2.1 Subsection

[Content goes here]

### 2.2 Another Subsection

[Content goes here]

## 3. Requirements (if applicable)

### 3.1 Functional Requirements

- **REQ-001**: System SHALL [requirement text]
- **REQ-002**: System SHALL [requirement text]

### 3.2 Non-Functional Requirements

- **REQ-003**: System SHALL [requirement text]

## 4. Additional Sections

[Add sections as needed]

---

## Notes for Using This Template

1. **YAML Front Matter** (lines 1-13):
   - Keep the `---` delimiters
   - Update all field values with your document information
   - `title`: Full document title
   - `author`: Primary author or team name
   - `department`: Usually "Engineering" for technical documents
   - `doc_number`: Dilon document number (format: DD_XXX_XXXXX)
   - `current_revision`: Current revision number
   - `regulatory_rep`, `quality_rep`, `department_head`: Names of approvers
   - `revisions`: Array of revision history entries
     - Add new entries for each revision
     - Include: `number`, `description`, `eco_number`, `eco_date`

2. **Document Content** (after front matter):
   - Use standard Markdown syntax
   - Headings: `##` for main sections, `###` for subsections
   - Lists: `-` for bullets, `1.` for numbered
   - Tables: Standard Markdown table syntax
   - Code blocks: Use triple backticks
   - Bold: `**text**`
   - Italic: `*text*`

3. **Generating Word Document**:
   ```bash
   python generate_dilon_doc.py your_document.md output_document.docx
   ```

4. **Adding Revisions**:
   When creating a new revision, add a new entry to the `revisions` array:
   ```yaml
   revisions:
     - number: "1.0"
       description: "Initial release"
       eco_number: "ECO-001"
       eco_date: "2025-09-25"
     - number: "1.1"
       description: "Updated requirements"
       eco_number: "ECO-002"
       eco_date: "2025-10-02"
   ```
   And update `current_revision` to match the latest revision number.

5. **Delete This Section**:
   Remove this "Notes for Using This Template" section before generating your final document.
