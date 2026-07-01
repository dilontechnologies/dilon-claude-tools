# Dilon Claude Tools - Test Suite

This directory contains tests for the Dilon Claude Tools Claude Code plugin (the `dilon-document-writer` and `dilon-document-compiler` skills).

## Test Files

### `run_tests.py`
Direct-invocation test suite (6 checks):
- A Python port of the `dilon-document-writer` stub-generation logic (that skill has no script of its own - its behavior is plain instructions in `SKILL.md` for Claude to follow - so this test ports the same substitution logic to exercise it automatically):
  1. Stub generation with custom parameters
  2. Stub generation with default parameters
  3. Refusal to overwrite an existing file
- Direct subprocess calls to `skills/dilon-document-compiler/scripts/generate_dilon_doc.py`:
  4. Non-zero exit code for a missing input file
  5. Successful compilation (exit 0, output file created) for a valid document
- It then invokes `validate-output.py` (its 5 checks below) and folds that result into the overall pass/fail.

### `validate-output.py`
Python validation script that validates generated outputs:
- Validates markdown stub structure and YAML front matter
- Validates compiled Word documents
- Checks `STYLING_TEST_TEMPLATE` files
- Verifies all required fields are present

### `STYLING_TEST_TEMPLATE.md` / `STYLING_TEST_TEMPLATE.docx`
Example template files used to test styling and compilation features.

## Running Tests

Run all tests from the repository root:

```bash
py -3 tests/run_tests.py
```

(On some Windows machines, bare `python`/`py` resolve through a shebang-re-resolution quirk to a package-less WindowsApps stub. `py -3` is the reliable invocation there.)

### What Gets Tested

**Direct-Invocation Checks (6 checks):**
1. Document stub generation (3 tests)
   - Custom parameters
   - Default parameters
   - Error handling (duplicate file)
2. Document compilation (2 tests)
   - Error handling (missing file)
   - Valid compilation
3. Output validation (invokes `validate-output.py`, see below)

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
  - `## Purpose and Scope`
  - `### Purpose`
  - `### Scope`

**Note:** The validation does NOT enforce that `current_revision` matches the revision numbers in the `revisions` list. It is the user's responsibility to keep these in sync.

### Word Document Validation
- File must exist and be a valid .docx
- Must have content (paragraphs)
- Should have at least 2 tables (signature + revision)
- Must have styles defined

## Expected Results

All tests should pass with:
- **Direct-invocation checks:** 6/6 passed
- **Validation checks:** 5/5 passed (100%)
- **Overall:** All tests passed! Exit code 0.

## Troubleshooting

### Python Dependencies
If validation or compilation fails, ensure Python dependencies are installed:
```bash
pip install python-docx python-docx-template docxcompose pyyaml
```

Or run the compiler skill's own dependency checker for a clearer report:
```bash
python skills/dilon-document-compiler/scripts/check_deps.py
```
Any `[FAIL]` line names the missing piece. `install.ps1` (repo root) can install Python/Pandoc/pip packages automatically.

### Unicode Errors
The validation script uses ASCII-compatible output (`[PASS]`, `[FAIL]`, `[INFO]`) to avoid Windows console encoding issues.
