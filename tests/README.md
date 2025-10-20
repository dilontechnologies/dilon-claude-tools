# Dilon Claude Tools - Test Suite

This directory contains comprehensive tests for the Dilon Claude Tools MCP server.

## Test Files

### `test-all-features.js`
Comprehensive integration test suite that tests all MCP server functionality:
- Server initialization
- Tool registration (dilon_compile_doc, dilon_plantuml, dilon_generate_stub)
- Resource registration (markdown and PlantUML styling guides)
- Resource content retrieval
- Tool execution and error handling
- Output validation

### `validate-output.py`
Python validation script that validates generated outputs:
- Validates markdown stub structure and YAML front matter
- Validates compiled Word documents
- Checks STYLING_TEST_TEMPLATE files
- Verifies all required fields are present

### `STYLING_TEST_TEMPLATE.md` / `STYLING_TEST_TEMPLATE.docx`
Example template files used to test styling and compilation features.

## Running Tests

### Quick Test
Run all tests from the repository root:

```bash
node tests/test-all-features.js
```

### What Gets Tested

**MCP Server Tests (18 checks):**
1. Server initialization
2. Tool registration (3 tools)
3. Resource registration (2 resources)
4. Resource content retrieval (2 resources)
5. Document stub generation (3 tests)
   - Custom parameters
   - Default parameters
   - Error handling (duplicate file)
6. Document compilation (2 tests)
   - Error handling (missing file)
   - Valid compilation
7. PlantUML tool (1 test)
   - Error handling (missing file)

**Output Validation (5 checks):**
1. Custom stub validation
2. Default stub validation
3. Compiled Word document validation
4. STYLING_TEST_TEMPLATE markdown validation
5. STYLING_TEST_TEMPLATE.docx validation

### Test Output

Test outputs are created in `tests/test-output/`:
- `custom_stub.md` - Generated with custom parameters
- `default_stub.md` - Generated with default parameters
- `compile_test.md` - Test markdown file
- `compile_test.docx` - Compiled Word document

## Validation Rules

### Markdown Stub Validation
- Must have valid YAML front matter (between `---` delimiters)
- Required YAML fields:
  - `title`, `author`, `department`, `doc_number`
  - `current_revision`, `regulatory_rep`, `quality_rep`, `department_head`
  - `revisions` (array)
- Each revision must have:
  - `number`, `description`, `eco_number`, `eco_date`
- Must contain sections:
  - `## 1. Purpose and Scope`
  - `### 1.1 Purpose`
  - `### 1.2 Scope`

**Note:** The validation does NOT enforce that `current_revision` matches the revision numbers in the `revisions` list. It is the user's responsibility to keep these in sync.

### Word Document Validation
- File must exist and be a valid .docx
- Must have content (paragraphs)
- Should have at least 2 tables (signature + revision)
- Must have styles defined

## Expected Results

All tests should pass with:
- **MCP Tests:** 18/18 passed (100%)
- **Validation Tests:** 5/5 passed (100%)
- **Overall:** All tests passed! Package is ready for release.

## Troubleshooting

### Python Dependencies
If validation fails, ensure Python dependencies are installed:
```bash
pip install python-docx pyyaml
```

### MCP Server Issues
If the server fails to start:
1. Check that `server.js` is in the repository root
2. Verify Node.js version >= 18.0.0
3. Run `npm install` to ensure dependencies are installed

### Unicode Errors
The validation script uses ASCII-compatible output (`[PASS]`, `[FAIL]`, `[INFO]`) to avoid Windows console encoding issues.
