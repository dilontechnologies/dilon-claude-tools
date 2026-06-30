# install.ps1
# Dependency setup for Dilon Claude Tools (Claude Code plugin)
#
# This script:
# 1. Checks for required dependencies (Python, Pandoc)
# 2. Installs missing dependencies automatically via winget
# 3. Installs required Python packages
# 4. Installs the Compile-DilonDoc / dilonc PowerShell alias

#Requires -RunAsAdministrator

param(
    [switch]$SkipDependencies,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dilon Claude Tools - Dependency Setup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$RepoRoot = $PSScriptRoot

# ============================================
# Dependency Detection Functions
# ============================================

function Test-CommandExists {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Get-PythonPath {
    if (Test-CommandExists "python") {
        $version = python --version 2>&1
        Write-Host "  [OK] Python found: $version" -ForegroundColor Green
        return "python"
    }
    return $null
}

function Get-PandocPath {
    if (Test-CommandExists "pandoc") {
        $version = pandoc --version 2>&1 | Select-Object -First 1
        Write-Host "  [OK] Pandoc found: $version" -ForegroundColor Green
        return "pandoc"
    }
    return $null
}

# ============================================
# Dependency Installation Functions
# ============================================

function Install-Winget {
    Write-Host "  -> Checking for winget..." -ForegroundColor Yellow

    if (Test-CommandExists "winget") {
        Write-Host "  [OK] winget already installed" -ForegroundColor Green
        return $true
    }

    Write-Host "  [WARN] winget not found. Please install Windows App Installer from Microsoft Store." -ForegroundColor Yellow
    Write-Host "     URL: https://aka.ms/getwinget" -ForegroundColor Yellow
    return $false
}

function Install-Python {
    Write-Host "  -> Installing Python..." -ForegroundColor Yellow

    if (-not (Install-Winget)) {
        Write-Host "  [FAIL] Cannot install Python without winget" -ForegroundColor Red
        return $false
    }

    try {
        winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Test-CommandExists "python") {
            Write-Host "  [OK] Python installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [WARN] Python installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  [FAIL] Failed to install Python: $_" -ForegroundColor Red
        return $false
    }
}

function Install-Pandoc {
    Write-Host "  -> Installing Pandoc..." -ForegroundColor Yellow

    if (-not (Install-Winget)) {
        Write-Host "  [FAIL] Cannot install Pandoc without winget" -ForegroundColor Red
        return $false
    }

    try {
        winget install --id JohnMacFarlane.Pandoc --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Test-CommandExists "pandoc") {
            Write-Host "  [OK] Pandoc installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [WARN] Pandoc installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  [FAIL] Failed to install Pandoc: $_" -ForegroundColor Red
        return $false
    }
}

# ============================================
# Main Installation Process
# ============================================

Write-Host "Step 1: Checking dependencies..." -ForegroundColor Cyan
Write-Host ""

$pythonPath = Get-PythonPath
$pandocPath = Get-PandocPath

# Install missing dependencies
if (-not $SkipDependencies) {
    Write-Host ""
    Write-Host "Step 2: Installing missing dependencies..." -ForegroundColor Cyan
    Write-Host ""

    if (-not $pythonPath) {
        if (Install-Python) {
            $pythonPath = "python"
        } else {
            Write-Host ""
            Write-Host "[FAIL] Python installation failed. Please install Python manually:" -ForegroundColor Red
            Write-Host "   https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }

    if (-not $pandocPath) {
        if (Install-Pandoc) {
            $pandocPath = "pandoc"
        } else {
            Write-Host ""
            Write-Host "[FAIL] Pandoc installation failed. Please install Pandoc manually:" -ForegroundColor Red
            Write-Host "   https://pandoc.org/installing.html" -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host "  [WARN] Skipping dependency installation (--SkipDependencies flag)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Installing Python dependencies..." -ForegroundColor Cyan
Write-Host ""

# Install Python packages required by the dilon-document-compiler skill
$requiredPackages = @("python-docx", "python-docx-template", "docxcompose", "pyyaml>=6.0")

foreach ($package in $requiredPackages) {
    Write-Host "  -> Installing $package..." -ForegroundColor Gray
    & python -m pip install $package --quiet
}

Write-Host "  [OK] Python dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Installing PowerShell command (optional)..." -ForegroundColor Cyan
Write-Host ""

# Install Compile-DilonDoc PowerShell function
$compilerScriptPath = Join-Path $RepoRoot "skills\dilon-document-compiler\scripts\generate_dilon_doc.py"
$signatureTemplatePath = Join-Path $RepoRoot "skills\dilon-document-compiler\templates\TEMPLATE_Word_Signature.docx"
$contentTemplatePath = Join-Path $RepoRoot "skills\dilon-document-compiler\templates\TEMPLATE_Word_Content.docx"

Write-Host "  -> Adding Compile-DilonDoc command to PowerShell profile..." -ForegroundColor Gray

$functionDefinition = @"
function Compile-DilonDoc {
    <#
    .SYNOPSIS
    Compiles a Markdown file to a formatted Dilon Word document.

    .DESCRIPTION
    Converts a Markdown file with YAML front matter to a properly formatted Word document
    using the Dilon Document Compiler.

    .PARAMETER InputMarkdown
    Path to the input Markdown file (.md)

    .PARAMETER OutputWord
    Path to the output Word file (.docx). Optional - defaults to same name as input with .docx extension.

    .PARAMETER SignatureTemplate
    Path to custom signature template. Optional - uses default if not specified.

    .PARAMETER ContentTemplate
    Path to custom content template. Optional - uses default if not specified.

    .EXAMPLE
    Compile-DilonDoc -InputMarkdown "MyDocument.md"

    .EXAMPLE
    Compile-DilonDoc "MyDocument.md" "Output.docx"
    #>

    [CmdletBinding()]
    param(
        [Parameter(Mandatory=`$true, Position=0)]
        [string]`$InputMarkdown,

        [Parameter(Position=1)]
        [string]`$OutputWord,

        [Parameter()]
        [string]`$SignatureTemplate,

        [Parameter()]
        [string]`$ContentTemplate
    )

    `$inputPath = Resolve-Path `$InputMarkdown -ErrorAction Stop

    if (-not `$OutputWord) {
        `$OutputWord = [System.IO.Path]::ChangeExtension(`$inputPath, ".docx")
    }

    if (-not `$SignatureTemplate) {
        `$SignatureTemplate = "$signatureTemplatePath"
    }

    if (-not `$ContentTemplate) {
        `$ContentTemplate = "$contentTemplatePath"
    }

    `$pythonArgs = @(
        "$compilerScriptPath",
        "`$inputPath",
        "`$OutputWord",
        "`$SignatureTemplate",
        "`$ContentTemplate"
    )

    Write-Host "Compiling document..." -ForegroundColor Cyan
    & python `$pythonArgs

    if (`$LASTEXITCODE -eq 0) {
        Write-Host "Document compiled successfully!" -ForegroundColor Green
        Write-Host "Output: `$OutputWord" -ForegroundColor Green
    } else {
        Write-Error "Document compilation failed!"
    }
}

Set-Alias -Name dilonc -Value Compile-DilonDoc
"@

# Get PowerShell profile path
$profilePath = $PROFILE.CurrentUserAllHosts

# Create profile if it doesn't exist
if (-not (Test-Path $profilePath)) {
    $profileDir = Split-Path $profilePath -Parent
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

# Read existing profile
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

# Check if function already exists
if ($profileContent -match "function Compile-DilonDoc") {
    # Remove old function
    $profileContent = $profileContent -replace "(?s)function Compile-DilonDoc.*?^}", ""
    $profileContent = $profileContent -replace "(?m)^Set-Alias -Name dilonc.*$", ""
    $profileContent = $profileContent.Trim()
}

# Append function
if ($profileContent) {
    $newContent = $profileContent + "`n`n# Dilon Document Compiler`n" + $functionDefinition
} else {
    $newContent = "# Dilon Document Compiler`n" + $functionDefinition
}

Set-Content -Path $profilePath -Value $newContent

Write-Host "  [OK] PowerShell command installed" -ForegroundColor Green
Write-Host "    - Compile-DilonDoc <input.md> [output.docx]" -ForegroundColor Gray
Write-Host "    - dilonc <input.md> [output.docx] (alias)" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Install the plugin in Claude Code:" -ForegroundColor White
Write-Host "     /plugin marketplace add dilontechnologies/dilon-claude-tools" -ForegroundColor Gray
Write-Host "     /plugin install dilon-tools@dilon-claude-tools" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  - README.md - Setup and usage guide" -ForegroundColor White
Write-Host ""
