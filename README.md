# Dilon Claude Tools

**Claude Code plugin for Dilon Technologies document authoring tools**

This repository is a [Claude Code plugin](https://code.claude.com/docs/en/plugins) that bundles two Skills for working with Dilon Technologies' regulatory-compliant technical documentation:

- **`dilon-document-writer`** - create a new Dilon document from the standard template, and apply Dilon markdown styling conventions while editing existing Dilon documents.
- **`dilon-document-compiler`** - compile a Dilon-formatted markdown file into a regulatory-compliant Word document (signature page, revision history table, table of contents).

## Prerequisites

- **Python** (>= 3.8) and the following pip packages: `python-docx`, `python-docx-template`, `docxcompose`, `pyyaml>=6.0`
- **Pandoc** (for Markdown to Word conversion), on PATH

Run `install.ps1` (as Administrator) from the repo root to auto-install these via winget and pip:

```powershell
cd C:\Users\YourUsername\Local_Documents\Local_Repos\dilon-claude-tools
.\install.ps1
```

This also installs the `Compile-DilonDoc` / `dilonc` PowerShell alias for compiling documents outside of Claude Code.

The `dilon-document-writer` skill has no external dependencies - it works without running `install.ps1`.

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
├── skills/
│   ├── dilon-document-writer/
│   │   ├── SKILL.md
│   │   ├── MARKDOWN_STYLING_GUIDE.md
│   │   └── TEMPLATE_Document.md
│   └── dilon-document-compiler/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── generate_dilon_doc.py
│       │   └── check_deps.py
│       └── templates/
│           ├── TEMPLATE_Word_Signature.docx
│           └── TEMPLATE_Word_Content.docx
├── install.ps1                   # dependency setup (Python, Pandoc, pip packages)
├── tests/
│   ├── run_tests.py
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
```

Requires the same Python/Pandoc prerequisites listed above. Use `py -3` explicitly rather than bare `python`/`py` — on some Windows setups those resolve through a shebang-re-resolution quirk to a package-less Microsoft Store stub instead of the real interpreter.

## Troubleshooting

### Plugin not found / skills don't trigger

1. Confirm the plugin installed: `/plugin list` should show `dilon-tools@dilon-claude-tools` as enabled.
2. Run `claude plugin validate .` from the repo root to check for manifest/skill errors.
3. Run `claude --debug` to see plugin loading details.

### Compilation fails with a missing-dependency error

Run the dependency checker directly:

```powershell
python skills/dilon-document-compiler/scripts/check_deps.py
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
