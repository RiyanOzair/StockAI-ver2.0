<#
PowerShell helper: clean_and_push_filtered_repo.ps1

WHAT IT DOES
- Creates a bare mirror of the current repo in a temp folder
- Uses git-filter-repo with replace rules to scrub OpenAI keys and related patterns
- Verifies the secret pattern no longer appears in history
- Force-pushes cleaned refs and tags to the provided remote

USAGE (review before running):
1) Open PowerShell in the repository root (C:\Users\...\StockAI).
2) Inspect the replacement patterns below and update `$RemoteUrl` if needed.
3) Run: `.	ools\clean_and_push_filtered_repo.ps1` (or run in place: `.	ools\clean_and_push_filtered_repo.ps1 -RemoteUrl 'https://github.com/you/yourrepo.git' -DryRun`)

IMPORTANT
- This performs a destructive history rewrite. All collaborators MUST reclone after the force-push.
- You should have rotated any exposed keys already (you mentioned you rotated them).
- The script attempts to auto-install `git-filter-repo` into a detected `venv` or uses user pip install; if installation fails it will stop.

ALTERNATIVE: BFG repo-cleaner instructions are included at the bottom as commented guidance.
#>
param(
    [string]$RemoteUrl = 'https://github.com/RiyanOzair/StockAI.git',
    [switch]$DryRun
)

function Abort($msg){ Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# Basic prerequisites
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Abort 'git not found in PATH. Install Git before continuing.' }

# Check for git-filter-repo
git filter-repo --version > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "git-filter-repo not found. Attempting to install via pip..." -ForegroundColor Yellow
    # Try to install into local venv if present
    if (Test-Path .\venv\Scripts\python.exe) {
        Write-Host "Installing into detected venv..." -ForegroundColor Yellow
        & .\venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
        & .\venv\Scripts\python.exe -m pip install git-filter-repo | Out-Null
    } else {
        Write-Host "No local venv detected. Attempting user install with python -m pip install --user git-filter-repo" -ForegroundColor Yellow
        python -m pip install --user git-filter-repo | Out-Null
    }
    git filter-repo --version > $null 2>&1
    if ($LASTEXITCODE -ne 0) { Abort 'git-filter-repo installation failed. Install manually: pip install git-filter-repo' }
}

# Prepare mirror
$RepoPath = (Get-Location).Path
$MirrorDir = Join-Path $env:TEMP ("stockai-mirror-{0}" -f ([System.Guid]::NewGuid().ToString('N')))
Write-Host "Creating mirror clone at: $MirrorDir" -ForegroundColor Cyan

if ($DryRun) { Write-Host "DRY RUN: No changes will be pushed." -ForegroundColor Yellow }

git clone --mirror $RepoPath $MirrorDir
if ($LASTEXITCODE -ne 0) { Abort 'mirror clone failed' }

# Build replacement rules
$ReplFile = Join-Path $MirrorDir 'replacements.txt'
@"
# git-filter-repo replacement rules
# Replace typical OpenAI-style keys and any OPENAI_API_KEY assignments
regex:sk-[A-Za-z0-9_\-]{10,}
==> [REDACTED_OPENAI_KEY]

# Replace explicit OPENAI_API_KEY assignment values
regex:OPENAI_API_KEY\s*=\s*".+"
==> OPENAI_API_KEY = ""

# Add any other patterns you want to redact below
"@ | Out-File -FilePath $ReplFile -Encoding utf8

Write-Host "Replacement file created: $ReplFile" -ForegroundColor Green

# Run filter-repo inside the mirror
Push-Location $MirrorDir
try {
    Write-Host "Running git-filter-repo (this rewrites history)..." -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "DRY RUN: Showing what would be rewritten (without push)." -ForegroundColor Yellow
        git filter-repo --replace-text $ReplFile --analyze
    } else {
        git filter-repo --force --replace-text $ReplFile
    }
} catch {
    Pop-Location
    Abort "git-filter-repo failed: $_"
}

# Quick verification: search for long 'sk-' tokens (likely API keys)
# Use a regex that matches 'sk-' followed by >=10 alphanumeric/_/- characters
$found = & git log --all -G "sk-[A-Za-z0-9_\-]{10,}" --pretty=format:'%H' -n 1 2>$null
if ($found) {
    Pop-Location
    Abort "Post-clean verification failed: long 'sk-' token still present in history (commit $found). Manual inspection required."
}

Write-Host "No long 'sk-' tokens found in cleaned mirror." -ForegroundColor Green

if ($DryRun) {
    Write-Host "DRY RUN complete. The mirror has been rewritten locally but nothing was pushed. Inspect $MirrorDir and run again without -DryRun to push." -ForegroundColor Yellow
    Pop-Location
    exit 0
}

# Push cleaned refs and tags to remote
Write-Host "Pushing cleaned history to $RemoteUrl (force)" -ForegroundColor Cyan

# Attempt to push; user must have permission / credential configured
$pushAll = (git push --force $RemoteUrl --all) -join "`n"
if ($LASTEXITCODE -ne 0) { Pop-Location; Abort "git push --all failed. Inspect credentials and remote access. Output:`n$pushAll" }

$pushTags = (git push --force $RemoteUrl --tags) -join "`n"
if ($LASTEXITCODE -ne 0) { Pop-Location; Abort "git push --tags failed. Inspect credentials and remote access. Output:`n$pushTags" }

Write-Host "Push complete. Remote history should now be rewritten." -ForegroundColor Green

Pop-Location

# Cleanup
try { Remove-Item -Recurse -Force $MirrorDir -ErrorAction SilentlyContinue } catch {}

Write-Host "Done. Important next steps:" -ForegroundColor Cyan
Write-Host "- Inform all collaborators to reclone the repository (old history replaced)." -ForegroundColor White
Write-Host "- Rotate any remaining keys and verify no secrets remain on CI or other services." -ForegroundColor White
Write-Host "- Verify GitHub push-protection quiets down; if GH still blocks, open the provided URL in the GitHub push-block message and request a review." -ForegroundColor White

# BFG alternative guidance
Write-Host "`n--- BFG ALTERNATIVE (instructions only) ---`n" -ForegroundColor Yellow
Write-Host "If you prefer the BFG repo-cleaner, the steps are: (1) mirror-clone, (2) run BFG to replace or delete the offending token, (3) run 'git reflog expire --expire=now --all && git gc --prune=now --aggressive', (4) force-push --all and --tags." -ForegroundColor White
Write-Host "Example BFG usage (not executed by this script):" -ForegroundColor White
Write-Host "  java -jar bfg.jar --replace-text replacements.txt repo.git" -ForegroundColor White

Write-Host "Script finished." -ForegroundColor Green
