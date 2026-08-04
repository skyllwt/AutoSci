# ============================================================================
# AutoSci - One-Click Setup for Qoder (Windows / PowerShell)
# ============================================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup-qoder.ps1            # English (default)
#   powershell -ExecutionPolicy Bypass -File .\setup-qoder.ps1 -Lang zh   # Chinese
#
# Mirrors setup.ps1 but targets Qoder instead of Claude Code:
#   prerequisites -> venv + deps -> config -> convert i18n skills into
#   .qoder/skills (tools/convert_to_qoder.py) -> verify.
# API key configuration (Semantic Scholar, DeepXiv, Review LLM) is handled
# interactively by Qoder - invoke the `setup` skill after opening the project.
# ============================================================================

[CmdletBinding()]
param(
    [ValidateSet("en", "zh")]
    [string]$Lang = "en"
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO]  $msg" -ForegroundColor Blue }
function Write-Ok($msg)   { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Fail($msg) { Write-Host "[FAIL]  $msg" -ForegroundColor Red }

$ProjectRoot = $PSScriptRoot
$I18nDir = Join-Path $ProjectRoot "i18n\$Lang"
if (-not (Test-Path $I18nDir)) {
    Write-Fail "i18n\$Lang not found - run from the project root"
    exit 1
}

Write-Host ""
Write-Host "============================================"
Write-Host "  AutoSci - Setup for Qoder (Windows)"
Write-Host "============================================"
Write-Host ""

# -- Step 1: Check prerequisites -------------------------------------------
Write-Info "Checking prerequisites..."

# Python: prefer `python`, fall back to `py -3`
$PythonCmd = $null
foreach ($candidate in @("python", "python3", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $PythonCmd = $candidate
        break
    }
}
if (-not $PythonCmd) {
    Write-Fail "Python not found. Install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
}

$pyVersionRaw = & $PythonCmd --version 2>&1
if ($pyVersionRaw -match "(\d+)\.(\d+)\.(\d+)") {
    $pyMajor = [int]$Matches[1]
    $pyMinor = [int]$Matches[2]
    if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 9)) {
        Write-Fail "Python >= 3.9 required, found $pyVersionRaw"
        exit 1
    }
    Write-Ok "Python $pyVersionRaw"
} else {
    Write-Fail "Could not parse Python version: $pyVersionRaw"
    exit 1
}

# pip
& $PythonCmd -m pip --version 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip not found. Run: $PythonCmd -m ensurepip"
    exit 1
}
Write-Ok "pip available"

# -- Step 2: Python environment + dependencies -----------------------------
Write-Host ""
Write-Info "Setting up Python environment..."

Push-Location $ProjectRoot
try {
    if ($env:VIRTUAL_ENV -or ($env:CONDA_DEFAULT_ENV -and $env:CONDA_DEFAULT_ENV -ne "base")) {
        Write-Warn2 "Active environment detected; setup always installs AutoSci into .venv"
    }

    if (Test-Path ".venv") {
        Write-Warn2 ".venv already exists, using it"
    } else {
        & $PythonCmd -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
        Write-Ok "Created .venv"
    }

    $VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $VenvPython)) {
        Write-Fail "Expected $VenvPython but it does not exist"
        exit 1
    }
    Write-Ok "Using .venv\Scripts\python.exe"

    Write-Info "Installing dependencies into .venv..."
    & $VenvPython -m pip install -r requirements.txt -q
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Write-Ok "Dependencies installed into .venv"

    # -- Step 3: Configuration files ---------------------------------------
    Write-Host ""
    Write-Info "Setting up configuration..."

    if (Test-Path ".env") {
        Write-Warn2 ".env already exists, not overwriting"
    } else {
        Copy-Item "config\.env.example" ".env"
        Write-Ok "Created .env from template"
    }

    if (-not (Test-Path ".qoder")) { New-Item -ItemType Directory -Path ".qoder" | Out-Null }

    # -- Step 3b: Convert i18n skills into Qoder-native assets -------------
    Write-Host ""
    Write-Info "Converting skills for Qoder (lang=$Lang)..."
    & $VenvPython (Join-Path $ProjectRoot "tools\convert_to_qoder.py") --lang $Lang --project-root $ProjectRoot
    if ($LASTEXITCODE -ne 0) { throw "convert_to_qoder.py failed" }
    Write-Ok "Qoder skills activated ($Lang)"

    # -- Step 4: Verify installation ---------------------------------------
    Write-Host ""
    Write-Info "Verifying installation..."

    $script:VerificationErrors = 0
    $script:VerificationWarnings = 0

    function Invoke-PythonCheck {
        param(
            [string]$Label,
            [string]$Code,
            [string]$WorkingDirectory = $ProjectRoot,
            [switch]$WarningOnly
        )

        Push-Location $WorkingDirectory
        try {
            & $VenvPython -c $Code 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Ok $Label
            } elseif ($WarningOnly) {
                Write-Warn2 $Label
                $script:VerificationWarnings++
            } else {
                Write-Fail $Label
                $script:VerificationErrors++
            }
        } finally {
            Pop-Location
        }
    }

    Invoke-PythonCheck -Label "PyMuPDF (fitz)" -Code "import fitz"
    Invoke-PythonCheck -Label "requests" -Code "import requests"
    Invoke-PythonCheck -Label "feedparser" -Code "import feedparser"

    $toolChecks = @(
        @{ name = "tools/init_discovery.py"; import = "from init_discovery import prepare_inputs" },
        @{ name = "tools/fetch_s2.py";       import = "from fetch_s2 import search" },
        @{ name = "tools/fetch_arxiv.py";    import = "from fetch_arxiv import fetch_recent" },
        @{ name = "tools/research_wiki.py";  import = "from research_wiki import slugify" },
        @{ name = "tools/lint.py";           import = "from lint import check_missing_fields" }
    )
    foreach ($c in $toolChecks) {
        Invoke-PythonCheck -Label $c.name -Code $c.import -WorkingDirectory (Join-Path $ProjectRoot "tools")
    }

    & $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $VenvPython -c "import deepxiv_sdk" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "deepxiv-sdk (optional)"
        } else {
            Write-Warn2 "deepxiv-sdk unavailable; DeepXiv features will degrade but setup can continue"
            $script:VerificationWarnings++
        }
    } else {
        Write-Warn2 "Python < 3.10 detected inside .venv; deepxiv-sdk may be unavailable, so DeepXiv features may degrade"
        $script:VerificationWarnings++
    }
} finally {
    Pop-Location
}

# -- Done ------------------------------------------------------------------
Write-Host ""
Write-Host "============================================"
if ($script:VerificationErrors -eq 0 -and $script:VerificationWarnings -eq 0) {
    Write-Host "  Setup complete!" -ForegroundColor Green
} elseif ($script:VerificationErrors -eq 0) {
    Write-Host "  Setup complete with $script:VerificationWarnings warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "  Setup complete with $script:VerificationErrors error(s) and $script:VerificationWarnings warning(s)" -ForegroundColor Yellow
}
Write-Host "============================================"
Write-Host ""
Write-Host "  Next steps:"
Write-Host ""
Write-Host "  1. Open this folder in Qoder. AGENTS.md is picked up automatically;"
Write-Host "     project skills were generated into .qoder\skills\."
Write-Host ""
Write-Host "  2. Register the llm-review MCP server (needed by /review, /rebuttal, ...):"
Write-Host "     .qoder\mcp.json was generated from config\mcp.qoder.json.example."
Write-Host "     If Qoder does not pick it up, add it manually in Qoder MCP settings:"
Write-Host "       command: .venv\Scripts\python.exe"
Write-Host "       args:    mcp-servers/llm-review/server.py"
Write-Host ""
Write-Host "  3. Complete API key configuration (guided) - ask Qoder to run the"
Write-Host "     'setup' skill."
Write-Host ""
Write-Host "  4. Then initialize your wiki - ask Qoder to run the 'init' skill:"
Write-Host "       init [your-research-topic]"
Write-Host ""
Write-Host "  For more, see README.md"
Write-Host ""
