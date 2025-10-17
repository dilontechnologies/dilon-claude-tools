# Install-DilonCompiler.ps1
# Creates a global PowerShell function for easy access to the Dilon Document Compiler

$scriptPath = $PSScriptRoot
$generatorScript = Join-Path $scriptPath "generate_dilon_doc.py"
$signatureTemplate = Join-Path $scriptPath "TEMPLATE_Word_Signature.docx"
$contentTemplate = Join-Path $scriptPath "TEMPLATE_Word_Content.docx"

# Check if the generator script exists
if (-not (Test-Path $generatorScript)) {
    Write-Error "Error: generate_dilon_doc.py not found at $generatorScript"
    exit 1
}

# Create the function definition
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
    Compile-DilonDoc -InputMarkdown "MyDocument.md" -OutputWord "Output.docx"

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

    # Resolve input path
    `$inputPath = Resolve-Path `$InputMarkdown -ErrorAction Stop

    # Generate output path if not specified
    if (-not `$OutputWord) {
        `$OutputWord = [System.IO.Path]::ChangeExtension(`$inputPath, ".docx")
    }

    # Build python command
    `$pythonArgs = @(
        "$generatorScript",
        "`$inputPath",
        "`$OutputWord"
    )

    # Add custom templates if specified
    if (`$SignatureTemplate) {
        `$pythonArgs += `$SignatureTemplate
        if (`$ContentTemplate) {
            `$pythonArgs += `$ContentTemplate
        } else {
            `$pythonArgs += "$contentTemplate"
        }
    } elseif (`$ContentTemplate) {
        `$pythonArgs += "$signatureTemplate"
        `$pythonArgs += `$ContentTemplate
    }

    # Execute the Python script
    Write-Host "Compiling document..." -ForegroundColor Cyan
    & python `$pythonArgs

    if (`$LASTEXITCODE -eq 0) {
        Write-Host "✅ Document compiled successfully!" -ForegroundColor Green
        Write-Host "Output: `$OutputWord" -ForegroundColor Green
    } else {
        Write-Error "❌ Document compilation failed!"
    }
}

# Alias for shorter command
Set-Alias -Name dilonc -Value Compile-DilonDoc
"@

# Get the PowerShell profile path
$profilePath = $PROFILE.CurrentUserAllHosts

# Check if profile exists, create if not
if (-not (Test-Path $profilePath)) {
    $profileDir = Split-Path $profilePath -Parent
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
    Write-Host "Created PowerShell profile at: $profilePath" -ForegroundColor Yellow
}

# Read existing profile content
$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue

# Check if function already exists
if ($profileContent -match "function Compile-DilonDoc") {
    Write-Host "⚠️  Compile-DilonDoc function already exists in profile." -ForegroundColor Yellow
    $response = Read-Host "Do you want to replace it? (y/n)"
    if ($response -ne 'y') {
        Write-Host "Installation cancelled." -ForegroundColor Yellow
        exit 0
    }

    # Remove old function
    $profileContent = $profileContent -replace "(?s)function Compile-DilonDoc.*?^}", ""
    $profileContent = $profileContent -replace "(?m)^Set-Alias -Name dilonc.*$", ""
    $profileContent = $profileContent.Trim()
}

# Append the function to the profile
if ($profileContent) {
    $newContent = $profileContent + "`n`n# Dilon Document Compiler`n" + $functionDefinition
} else {
    $newContent = "# Dilon Document Compiler`n" + $functionDefinition
}

Set-Content -Path $profilePath -Value $newContent

Write-Host "`n✅ Dilon Document Compiler installed successfully!" -ForegroundColor Green
Write-Host "`nThe following commands are now available:" -ForegroundColor Cyan
Write-Host "  • Compile-DilonDoc <input.md> [output.docx]" -ForegroundColor White
Write-Host "  • dilonc <input.md> [output.docx]            (short alias)" -ForegroundColor White
Write-Host "`nExamples:" -ForegroundColor Cyan
Write-Host "  Compile-DilonDoc MyDocument.md" -ForegroundColor White
Write-Host "  dilonc MyDocument.md Output.docx" -ForegroundColor White
Write-Host "`nTo use these commands, restart your PowerShell session or run:" -ForegroundColor Yellow
Write-Host "  . `$PROFILE" -ForegroundColor White
