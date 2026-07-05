# ============================================================================
# AutoSci - One-Click Setup (Windows / PowerShell)
# ============================================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1            # English (default)
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Lang zh   # Chinese
#
# Mirrors setup.sh: prerequisites -> venv + deps -> config -> activate i18n -> verify.
# API key configuration (Semantic Scholar, DeepXiv, Review LLM) is handled
# interactively by your coding agent - run /setup in Claude Code or $setup in Codex.
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
Write-Host "  AutoSci - Setup (Windows)"
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

$HaveClaude = $false
$HaveCodex = $false
if (Get-Command claude -ErrorAction SilentlyContinue) {
    $HaveClaude = $true
    Write-Ok "Claude Code installed"
} else {
    Write-Warn2 "Claude Code not found."
}

if (Get-Command codex -ErrorAction SilentlyContinue) {
    $HaveCodex = $true
    Write-Ok "Codex installed"
} else {
    Write-Warn2 "Codex not found."
}

if (-not $HaveClaude -and -not $HaveCodex) {
    Write-Host ""
    Write-Host "  Install at least one coding-agent runtime to use AutoSci skills:"
    Write-Host "    npm install -g @anthropic-ai/claude-code"
    Write-Host "    # or install Codex from your OpenAI/Codex setup path"
    Write-Host ""
    $reply = Read-Host "  Continue setup without a coding agent? [y/N]"
    if ($reply -notmatch '^[Yy]$') {
        Write-Host "  Install Claude Code or Codex first, then re-run setup.ps1"
        exit 1
    }
}

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
        Copy-Item ".env.example" ".env"
        Write-Ok "Created .env from template"
    }

    if (-not (Test-Path ".claude")) { New-Item -ItemType Directory -Path ".claude" | Out-Null }
    if (Test-Path ".claude\settings.local.json") {
        Write-Warn2 ".claude\settings.local.json already exists, not overwriting"
    } else {
        Copy-Item "config\settings.local.json.example" ".claude\settings.local.json"
        Write-Ok "Created .claude\settings.local.json"
    }

    # -- Step 3b: Activate language files ----------------------------------
    Write-Host ""
    Write-Info "Activating language: $Lang"
    Copy-Item (Join-Path $I18nDir "CLAUDE.md") "CLAUDE.md" -Force
    $AgentsSource = Join-Path $I18nDir "AGENTS.md"
    if (Test-Path $AgentsSource) {
        Copy-Item $AgentsSource "AGENTS.md" -Force
    }

    $skillsSrc = Join-Path $I18nDir "skills"
    foreach ($agentSkillsDir in @(".claude\skills", ".agents\skills")) {
        if (-not (Test-Path $agentSkillsDir)) { New-Item -ItemType Directory -Path $agentSkillsDir -Force | Out-Null }
        Get-ChildItem -Path $skillsSrc -Directory | ForEach-Object {
            $name = $_.Name
            $destDir = Join-Path $agentSkillsDir $name
            if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
            Copy-Item (Join-Path $_.FullName "*") $destDir -Recurse -Force
        }

        $sharedDest = Join-Path $agentSkillsDir "shared-references"
        if (-not (Test-Path $sharedDest)) { New-Item -ItemType Directory -Path $sharedDest -Force | Out-Null }
        Get-ChildItem -Path (Join-Path $I18nDir "shared-references") -Filter "*.md" | ForEach-Object {
            Copy-Item $_.FullName (Join-Path $sharedDest $_.Name) -Force
        }
    }
    # Avoid naming collision with OpenCode's built-in init command
    $initSkill = Join-Path ".opencode\skills\init" "SKILL.md"
    if (Test-Path $initSkill) {
        (Get-Content $initSkill -Raw) -replace '(?m)^name: init$', 'name: autosci-init' | Set-Content $initSkill -NoNewline
        Rename-Item -Path ".opencode\skills\init" -NewName "autosci-init"
    }

    Set-Content -Path ".claude\.current-lang" -Value $Lang -NoNewline
    if (-not (Test-Path ".agents")) { New-Item -ItemType Directory -Path ".agents" -Force | Out-Null }
    Set-Content -Path ".agents\.current-lang" -Value $Lang -NoNewline
    Write-Ok "Language files activated for Claude Code and Codex ($Lang)"

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
Write-Host "  1. Authenticate your coding agent (if not already):"
Write-Host "       claude login"
Write-Host "       codex"
Write-Host ""
Write-Host "  2. Activate the venv in your shell only if you want to run Python tools manually:"
Write-Host "       .\.venv\Scripts\Activate.ps1"
Write-Host "       setup.ps1 does not activate your current shell permanently."
Write-Host "       /init will use .venv automatically when it exists."
Write-Host ""
Write-Host "  3. Start an agent:"
Write-Host "       claude"
Write-Host "       codex"
Write-Host ""
Write-Host "  4. Complete API key configuration (guided):"
Write-Host "       Claude Code: /setup"
Write-Host "       Codex:       `$setup"
Write-Host "       OpenCode:    run the setup skill"
Write-Host ""
Write-Host "  5. Then initialize your wiki:"
Write-Host "       Claude Code: /init [your-research-topic]"
Write-Host "       Codex:       `$init [your-research-topic]"
Write-Host "       OpenCode:    run the autosci-init skill [your-research-topic]"
Write-Host ""
Write-Host "  For more, see README.md"
Write-Host ""
