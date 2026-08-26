# Dilon Claude Tools

**Claude Code plugin for Dilon Technologies document authoring tools**

This repository is a [Claude Code plugin](https://code.claude.com/docs/en/plugins) that bundles five Skills for working with Dilon Technologies' regulatory-compliant technical documentation:

- **`dilon-document-writer`** - create a new Dilon document from the standard template, and apply Dilon markdown styling conventions while editing existing Dilon documents.
- **`dilon-document-compiler`** - compile a Dilon-formatted markdown file into a regulatory-compliant Word document (signature page, revision history table, table of contents).
- **`dilon-document-form-writer`** - create a new Dilon form/traveler document from its own template, and document the form-only markdown markers (`FillLine`, `FieldGrid`, `Form_Section_Header`).
- **`dilon-document-form-compiler`** - compile a Dilon form/traveler markdown file into a Word document with a running header/footer only (no title page, signature page, or table of contents).
- **`dilon-document-extractor`** - bootstrap a Dilon markdown draft from an existing Word or PDF document.

## Prerequisites

- **Python** (>= 3.8) and the following pip packages: `python-docx`, `docxcompose>=2.2.0`, `pyyaml>=6.0`, `pymupdf`, `jinja2`
- **Pandoc** (for Markdown to Word conversion), on PATH

Clone the repository, then run `install.ps1` (as Administrator) from the repo root to auto-install these via winget and pip:

```powershell
git clone https://github.com/dilontechnologies/dilon-claude-tools.git C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
cd C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
.\install.ps1
```

This also installs the `Compile-DilonDoc` / `dilonc` PowerShell alias for compiling documents outside of Claude Code.

The `dilon-document-writer` and `dilon-document-form-writer` skills have no external dependencies - they work without running `install.ps1`. The `dilon-document-extractor` skill's PDF path needs `pymupdf`, also installed by `install.ps1`.

> **If Claude is installing this for you:** `install.ps1` requires an elevated (Administrator) PowerShell session and installs software system-wide via winget (Python, Pandoc). Claude should not run `git clone` or `install.ps1` itself - run those two commands yourself in your own elevated terminal. Claude can then run the `/plugin marketplace add` / `/plugin install` commands below directly, in your regular Claude Code session.

## Installing the plugin

This repo is its own [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces). From within Claude Code:

```
/plugin marketplace add dilontechnologies/dilon-claude-tools
/plugin install dilon-tools@dilon-claude-tools
```

Authentication uses your existing git credentials (PAT or SSH) for this private repository - the same access you already use to `git clone` it.

### Updating

```
/plugin marketplace update dilon-claude-tools
/plugin update dilon-tools@dilon-claude-tools
```

### Testing locally before relying on the marketplace

```
/plugin marketplace add ./dilon-claude-tools
/plugin install dilon-tools@dilon-claude-tools
```

(Run from the parent directory of a local clone, or substitute the absolute path.)

## Usage

Once installed, just describe what you want in conversation - the skills trigger automatically:

```
User: "Create a new Dilon document for a software requirements spec"

Claude: *uses dilon-document-writer skill*
        Creates the new markdown file from the template with your supplied metadata.
```

```
User: "Compile Documentation/Requirements.md to a Word document"

Claude: *uses dilon-document-compiler skill*
        Document compiled successfully!
        Input:  Documentation/Requirements.md
        Output: Documentation/Requirements.docx
```

## Repository structure

```
dilon-claude-tools/
├── CLAUDE.md                     # project knowledge doc for Claude Code sessions
├── .claude-plugin/
│   ├── plugin.json              # plugin manifest
│   └── marketplace.json         # self-hosted marketplace listing this plugin
├── templates/                    # shared Word reference templates
│   ├── TEMPLATE_Word_Base.docx  # header/footer + styles only, shared by both compiler skills
│   └── assets/
│       └── dilon_logo.png        # header logo
├── lib/
│   └── dilon_docx_common.py      # Pandoc-conversion/styling helpers shared by both compiler skills
├── skills/
│   ├── dilon-document-writer/
│   │   ├── SKILL.md
│   │   ├── MARKDOWN_STYLING_GUIDE.md
│   │   └── TEMPLATE_Document.md
│   ├── dilon-document-compiler/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── generate_dilon_doc.py
│   │       ├── read_docx_sizes.py
│   │       └── check_deps.py
│   ├── dilon-document-form-writer/
│   │   ├── SKILL.md
│   │   └── TEMPLATE_Form.md
│   ├── dilon-document-form-compiler/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── generate_dilon_form.py
│   │       ├── form_fields.py
│   │       └── check_deps.py
│   └── dilon-document-extractor/
│       ├── SKILL.md
│       └── scripts/
│           ├── extract_docx.py
│           ├── extract_pdf.py
│           └── check_deps.py
├── install.ps1                   # dependency setup (Python, Pandoc, pip packages)
├── tests/
│   ├── run_tests.py
│   ├── run_form_tests.py
│   ├── run_extractor_tests.py
│   ├── validate-output.py
│   ├── README.md
│   ├── STYLING_TEST_TEMPLATE.md
│   ├── STYLING_TEST_TEMPLATE.docx
│   └── diagrams/                 # figures referenced by STYLING_TEST_TEMPLATE.md
└── CHANGELOG.md
```

## Running tests

```powershell
py -3 tests/run_tests.py
py -3 tests/run_extractor_tests.py
```

Requires the same Python/Pandoc prerequisites listed above. Use `py -3` explicitly rather than bare `python`/`py` — on some Windows setups those resolve through a shebang-re-resolution quirk to a package-less Microsoft Store stub instead of the real interpreter.

## Troubleshooting

### Plugin not found / skills don't trigger

1. Confirm the plugin installed: `/plugin list` should show `dilon-tools@dilon-claude-tools` as enabled.
2. Run `claude plugin validate .` from the repo root to check for manifest/skill errors.
3. Run `claude --debug` to see plugin loading details.

### Compilation or extraction fails with a missing-dependency error

Run the relevant dependency checker directly:

```powershell
python skills/dilon-document-compiler/scripts/check_deps.py
python skills/dilon-document-extractor/scripts/check_deps.py
```

Any `[FAIL]` line names the missing piece. Re-run `install.ps1` to fix Python/Pandoc/pip packages.

### Pandoc not found

```powershell
pandoc --version
```

If this fails, install Pandoc from https://pandoc.org/installing.html and ensure it's on PATH.

## License

Internal use only - Dilon Technologies LLC

## Support

Contact the Engineering Department.
