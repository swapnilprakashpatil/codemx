#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy CodeMx to GitHub Pages

.DESCRIPTION
    Prepares and pushes the application to GitHub for automatic deployment to GitHub Pages.
    Verifies all required files are present before committing.
#>

param(
    [string]$Message = "Deploy to GitHub Pages",
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║    CodeMx Deployment to GitHub      ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Verify Requirements ──────────────────────────────────────────────────────
Write-Host "  [CHECK] Verifying deployment requirements..." -ForegroundColor Yellow

# Check if git is configured
try {
    $gitUser = git config user.name
    $gitEmail = git config user.email
    if (-not $gitUser -or -not $gitEmail) {
        Write-Host "  [CHECK] ✗ Git not configured" -ForegroundColor Red
        Write-Host "  [CHECK] Run: git config --global user.name 'Your Name'" -ForegroundColor Gray
        Write-Host "  [CHECK] Run: git config --global user.email 'your@email.com'" -ForegroundColor Gray
        exit 1
    }
    Write-Host "  [CHECK] ✓ Git configured ($gitUser <$gitEmail>)" -ForegroundColor Green
} catch {
    Write-Host "  [CHECK] ✗ Git not found" -ForegroundColor Red
    exit 1
}

# Check if remote is set
try {
    $remote = git remote get-url origin
    Write-Host "  [CHECK] ✓ Git remote: $remote" -ForegroundColor Green
} catch {
    Write-Host "  [CHECK] ✗ Git remote not configured" -ForegroundColor Red
    Write-Host "  [CHECK] Run: git remote add origin https://github.com/swapnilprakashpatil/codemx.git" -ForegroundColor Gray
    exit 1
}

# Check if database exists
$dbPath = Join-Path $root "frontend\public\data\coding_database.sqlite.gz"
if (-not (Test-Path $dbPath)) {
    Write-Host "  [CHECK] ✗ Compressed database not found" -ForegroundColor Red
    Write-Host "  [CHECK] Run: python -m backend.pipeline.export_sqlite_browser --compress" -ForegroundColor Gray
    exit 1
}

$dbSize = (Get-Item $dbPath).Length / 1MB
Write-Host "  [CHECK] ✓ Database found: $([math]::Round($dbSize, 2)) MB" -ForegroundColor Green

# Check if workflow exists
$workflowPath = Join-Path $root ".github\workflows\deploy-pages.yml"
if (-not (Test-Path $workflowPath)) {
    Write-Host "  [CHECK] ✗ GitHub Actions workflow not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [CHECK] ✓ GitHub Actions workflow ready" -ForegroundColor Green

Write-Host ""

# ── Show Git Status ──────────────────────────────────────────────────────────
Write-Host "  [GIT] Current status:" -ForegroundColor Cyan
Write-Host ""
git status --short
Write-Host ""

# ── Commit and Push ──────────────────────────────────────────────────────────
if ($DryRun) {
    Write-Host "  [DRY-RUN] Would execute:" -ForegroundColor Yellow
    Write-Host "    git add ." -ForegroundColor Gray
    Write-Host "    git commit -m '$Message'" -ForegroundColor Gray
    Write-Host "    git push origin main" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [DRY-RUN] Run without -DryRun to actually deploy" -ForegroundColor Yellow
    exit 0
}

# Confirm before proceeding
Write-Host "  [DEPLOY] Ready to deploy to GitHub Pages" -ForegroundColor Yellow
Write-Host "  [DEPLOY] Commit message: '$Message'" -ForegroundColor Gray
Write-Host ""
$confirm = Read-Host "  [DEPLOY] Continue? (y/N)"

if ($confirm -ne 'y' -and $confirm -ne 'Y') {
    Write-Host "  [DEPLOY] Cancelled by user" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "  [GIT] Adding files..." -ForegroundColor Cyan
git add .

Write-Host "  [GIT] Committing changes..." -ForegroundColor Cyan
git commit -m $Message

Write-Host "  [GIT] Pushing to GitHub..." -ForegroundColor Cyan
git push origin main

Write-Host ""
Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║       Deployment Initiated!          ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host "  1. Go to: https://github.com/swapnilprakashpatil/codemx/actions" -ForegroundColor Gray
Write-Host "  2. Watch the 'Deploy to GitHub Pages' workflow" -ForegroundColor Gray
Write-Host "  3. Wait for ✓ (takes ~2-5 minutes)" -ForegroundColor Gray
Write-Host "  4. Visit: https://swapnilprakashpatil.github.io/codemx/" -ForegroundColor Gray
Write-Host ""
Write-Host "  Enable GitHub Pages:" -ForegroundColor Yellow
Write-Host "  1. Go to: https://github.com/swapnilprakashpatil/codemx/settings/pages" -ForegroundColor Gray
Write-Host "  2. Source: Select 'GitHub Actions'" -ForegroundColor Gray
Write-Host "  3. Save" -ForegroundColor Gray
Write-Host ""
