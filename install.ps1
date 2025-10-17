# install.ps1
# Installation script for Dilon Claude Tools MCP Server
#
# This script:
# 1. Checks for required dependencies (Python, Pandoc, Java, PlantUML)
# 2. Installs missing dependencies automatically
# 3. Configures the MCP server
# 4. Registers the server with Claude Code

#Requires -RunAsAdministrator

param(
    [switch]$SkipDependencies,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Dilon Claude Tools MCP Server Setup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script and repo directories
$RepoRoot = $PSScriptRoot
$ConfigPath = Join-Path $RepoRoot ".dilon-tools-config.json"
$ExampleConfigPath = Join-Path $RepoRoot ".dilon-tools-config.example.json"

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
        Write-Host "  ✓ Python found: $version" -ForegroundColor Green
        return "python"
    }
    return $null
}

function Get-PandocPath {
    if (Test-CommandExists "pandoc") {
        $version = pandoc --version 2>&1 | Select-Object -First 1
        Write-Host "  ✓ Pandoc found: $version" -ForegroundColor Green
        return "pandoc"
    }
    return $null
}

function Get-JavaPath {
    if (Test-CommandExists "java") {
        $version = java -version 2>&1 | Select-Object -First 1
        Write-Host "  ✓ Java found: $version" -ForegroundColor Green
        return "java"
    }
    return $null
}

function Get-PlantUMLPath {
    # Check common installation locations
    $commonPaths = @(
        "C:\Program Files\PlantUML",
        "C:\PlantUML",
        "$env:LOCALAPPDATA\PlantUML",
        "$env:ProgramFiles\PlantUML"
    )

    foreach ($path in $commonPaths) {
        $jarPath = Join-Path $path "plantuml.jar"
        if (Test-Path $jarPath) {
            Write-Host "  ✓ PlantUML found: $path" -ForegroundColor Green
            return $path
        }
    }

    return $null
}

# ============================================
# Dependency Installation Functions
# ============================================

function Install-Winget {
    Write-Host "  → Checking for winget..." -ForegroundColor Yellow

    if (Test-CommandExists "winget") {
        Write-Host "  ✓ winget already installed" -ForegroundColor Green
        return $true
    }

    Write-Host "  ⚠️  winget not found. Please install Windows App Installer from Microsoft Store." -ForegroundColor Yellow
    Write-Host "     URL: https://aka.ms/getwinget" -ForegroundColor Yellow
    return $false
}

function Install-Python {
    Write-Host "  → Installing Python..." -ForegroundColor Yellow

    if (-not (Install-Winget)) {
        Write-Host "  ❌ Cannot install Python without winget" -ForegroundColor Red
        return $false
    }

    try {
        winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Test-CommandExists "python") {
            Write-Host "  ✓ Python installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ⚠️  Python installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  ❌ Failed to install Python: $_" -ForegroundColor Red
        return $false
    }
}

function Install-Pandoc {
    Write-Host "  → Installing Pandoc..." -ForegroundColor Yellow

    if (-not (Install-Winget)) {
        Write-Host "  ❌ Cannot install Pandoc without winget" -ForegroundColor Red
        return $false
    }

    try {
        winget install --id JohnMacFarlane.Pandoc --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Test-CommandExists "pandoc") {
            Write-Host "  ✓ Pandoc installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ⚠️  Pandoc installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  ❌ Failed to install Pandoc: $_" -ForegroundColor Red
        return $false
    }
}

function Install-Java {
    Write-Host "  → Installing Java..." -ForegroundColor Yellow

    if (-not (Install-Winget)) {
        Write-Host "  ❌ Cannot install Java without winget" -ForegroundColor Red
        return $false
    }

    try {
        winget install --id EclipseAdoptium.Temurin.21.JRE --silent --accept-package-agreements --accept-source-agreements

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Test-CommandExists "java") {
            Write-Host "  ✓ Java installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ⚠️  Java installed but not in PATH. You may need to restart your terminal." -ForegroundColor Yellow
            return $true
        }
    } catch {
        Write-Host "  ❌ Failed to install Java: $_" -ForegroundColor Red
        return $false
    }
}

function Install-PlantUML {
    Write-Host "  → Installing PlantUML..." -ForegroundColor Yellow

    $installPath = "C:\Program Files\PlantUML"
    $jarPath = Join-Path $installPath "plantuml.jar"

    # Create directory if it doesn't exist
    if (-not (Test-Path $installPath)) {
        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    }

    try {
        # Download latest PlantUML jar
        $downloadUrl = "https://github.com/plantuml/plantuml/releases/download/v1.2024.3/plantuml-1.2024.3.jar"
        Write-Host "    Downloading PlantUML from GitHub..." -ForegroundColor Gray

        Invoke-WebRequest -Uri $downloadUrl -OutFile $jarPath -UseBasicParsing

        if (Test-Path $jarPath) {
            Write-Host "  ✓ PlantUML installed to: $installPath" -ForegroundColor Green

            # Create a helper script for easy invocation
            $helperScript = @"
@echo off
java -jar "$jarPath" %*
"@
            $helperPath = Join-Path $installPath "plantuml.bat"
            Set-Content -Path $helperPath -Value $helperScript

            # Add to PATH if not already there
            $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
            if ($currentPath -notlike "*$installPath*") {
                [Environment]::SetEnvironmentVariable("Path", "$currentPath;$installPath", "Machine")
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
            }

            Write-Host "  ✓ PlantUML command added to PATH" -ForegroundColor Green
            return $installPath
        }

        return $null
    } catch {
        Write-Host "  ❌ Failed to install PlantUML: $_" -ForegroundColor Red
        return $null
    }
}

# ============================================
# Main Installation Process
# ============================================

Write-Host "Step 1: Checking dependencies..." -ForegroundColor Cyan
Write-Host ""

$pythonPath = Get-PythonPath
$pandocPath = Get-PandocPath
$javaPath = Get-JavaPath
$plantUMLPath = Get-PlantUMLPath

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
            Write-Host "❌ Python installation failed. Please install Python manually:" -ForegroundColor Red
            Write-Host "   https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }

    if (-not $pandocPath) {
        if (Install-Pandoc) {
            $pandocPath = "pandoc"
        } else {
            Write-Host ""
            Write-Host "❌ Pandoc installation failed. Please install Pandoc manually:" -ForegroundColor Red
            Write-Host "   https://pandoc.org/installing.html" -ForegroundColor Yellow
            exit 1
        }
    }

    if (-not $javaPath) {
        if (Install-Java) {
            $javaPath = "java"
        } else {
            Write-Host ""
            Write-Host "❌ Java installation failed. Please install Java manually:" -ForegroundColor Red
            Write-Host "   https://adoptium.net/" -ForegroundColor Yellow
            exit 1
        }
    }

    if (-not $plantUMLPath) {
        $plantUMLPath = Install-PlantUML
        if (-not $plantUMLPath) {
            Write-Host ""
            Write-Host "❌ PlantUML installation failed. Please install manually:" -ForegroundColor Red
            Write-Host "   1. Download plantuml.jar from https://plantuml.com/download" -ForegroundColor Yellow
            Write-Host "   2. Place it in C:\Program Files\PlantUML\" -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host "  ⚠️  Skipping dependency installation (--SkipDependencies flag)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 3: Installing Python dependencies..." -ForegroundColor Cyan
Write-Host ""

# Install Python packages required by Dilon Document Compiler
$requiredPackages = @("python-docx", "python-docx-template", "docxcompose", "pyyaml")

foreach ($package in $requiredPackages) {
    Write-Host "  → Installing $package..." -ForegroundColor Gray
    & python -m pip install $package --quiet
}

Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "Step 4: Installing Node.js dependencies..." -ForegroundColor Cyan
Write-Host ""

Push-Location $RepoRoot
try {
    npm install
    Write-Host "  ✓ Node.js dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Failed to install Node.js dependencies: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Step 5: Creating configuration file..." -ForegroundColor Cyan
Write-Host ""

# Create user config from example if it doesn't exist
if ((Test-Path $ConfigPath) -and -not $Force) {
    Write-Host "  ⚠️  Configuration file already exists: $ConfigPath" -ForegroundColor Yellow
    $response = Read-Host "    Overwrite? (y/n)"
    if ($response -ne 'y') {
        Write-Host "  → Keeping existing configuration" -ForegroundColor Gray
    } else {
        Remove-Item $ConfigPath -Force
    }
}

if (-not (Test-Path $ConfigPath)) {
    $config = @{
        pythonPath = if ($pythonPath) { $pythonPath } else { "python" }
        plantUmlPath = if ($plantUMLPath) { $plantUMLPath } else { "C:\Program Files\PlantUML" }
        pandocPath = if ($pandocPath) { $pandocPath } else { "pandoc" }
    }

    $config | ConvertTo-Json | Set-Content -Path $ConfigPath
    Write-Host "  ✓ Configuration file created: $ConfigPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 6: Registering MCP server with Claude Code..." -ForegroundColor Cyan
Write-Host ""

# Locate Claude Code config
$claudeConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"

if (-not (Test-Path $claudeConfigPath)) {
    Write-Host "  ⚠️  Claude Code config not found at: $claudeConfigPath" -ForegroundColor Yellow
    Write-Host "  → Creating new config file..." -ForegroundColor Gray

    $claudeConfigDir = Split-Path $claudeConfigPath -Parent
    if (-not (Test-Path $claudeConfigDir)) {
        New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null
    }

    $claudeConfig = @{
        mcpServers = @{
            "dilon-claude-tools" = @{
                command = "node"
                args = @("$RepoRoot\server.js")
            }
        }
    }

    $claudeConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $claudeConfigPath
    Write-Host "  ✓ MCP server registered with Claude Code" -ForegroundColor Green
} else {
    # Update existing config
    $claudeConfig = Get-Content $claudeConfigPath -Raw | ConvertFrom-Json

    if (-not $claudeConfig.mcpServers) {
        $claudeConfig | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue @{} -Force
    }

    $claudeConfig.mcpServers | Add-Member -NotePropertyName "dilon-claude-tools" -NotePropertyValue @{
        command = "node"
        args = @("$RepoRoot\server.js")
    } -Force

    $claudeConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $claudeConfigPath
    Write-Host "  ✓ MCP server registered with Claude Code" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✓ Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Restart Claude Code to load the MCP server" -ForegroundColor White
Write-Host "  2. The following tools will be available:" -ForegroundColor White
Write-Host "     • dilon_compile_doc - Compile Markdown to Word documents" -ForegroundColor Gray
Write-Host "     • dilon_plantuml - Generate diagrams from PlantUML files" -ForegroundColor Gray
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Cyan
Write-Host "  • README.md - Setup and usage guide" -ForegroundColor White
Write-Host "  • docs/MARKDOWN_STYLING_GUIDE.md - Markdown formatting reference" -ForegroundColor White
Write-Host "  • docs/PlantUML_Style_Guide.md - PlantUML diagram standards" -ForegroundColor White
Write-Host ""
