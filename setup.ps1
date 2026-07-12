[CmdletBinding()]
param([ValidateSet("en", "zh")][string]$Lang = "en")
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Source = Join-Path $Root "i18n\$Lang"
Push-Location $Root
try {
  $Python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $Python) { $Python = Get-Command python3 -ErrorAction Stop }
  & $Python.Source -c "import sys; raise SystemExit(sys.version_info < (3, 9))"
  if ($LASTEXITCODE -ne 0) { throw "Python 3.9+ is required" }
  if (Get-Command opencode -ErrorAction SilentlyContinue) { Write-Host "[AutoSci] OpenCode found" }
  else { Write-Warning "OpenCode was not found; setup will still prepare the project." }
  if (-not (Test-Path .venv)) { & $Python.Source -m venv .venv }
  $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
  & $VenvPython -m pip install -q -r requirements.txt -r mcp-servers/llm-review/requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }
  if (-not (Test-Path .env)) { Copy-Item .env.example .env }
  Remove-Item .opencode\skills -Recurse -Force -ErrorAction SilentlyContinue
  New-Item .opencode\skills\shared-references -ItemType Directory -Force | Out-Null
  Copy-Item "$Source\skills\*" .opencode\skills -Recurse -Force
  Copy-Item "$Source\shared-references\*.md" .opencode\skills\shared-references -Force
  Copy-Item "$Source\AGENTS.md" AGENTS.md -Force
  Set-Content .opencode\.current-lang $Lang
  $Config = @{
    '$schema'='https://opencode.ai/config.json'
    mcp=@{'llm-review'=@{type='local';command=@((Resolve-Path $VenvPython).Path,(Resolve-Path 'mcp-servers\llm-review\server.py').Path);enabled=$true}}
    permission=@{skill='allow';task='allow';question='allow';websearch='allow';webfetch='allow';read='allow';glob='allow';grep='allow';list='allow';edit='ask';bash='ask'}
  }
  $Config | ConvertTo-Json -Depth 8 | Set-Content opencode.json -Encoding UTF8
  & $VenvPython -c "import fitz, requests, feedparser, httpx"
  & $VenvPython -m py_compile mcp-servers/llm-review/server.py tools/daily_arxiv.py
  Write-Host "[AutoSci] Installed language=$Lang. Start with: opencode"
  Write-Host "[AutoSci] Use the init skill to initialize the research wiki."
} finally { Pop-Location }
