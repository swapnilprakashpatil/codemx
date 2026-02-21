<#
.SYNOPSIS
    Downloads the FDA NDC (National Drug Code) directory file.
.DESCRIPTION
    Downloads the ndctext.zip file from the FDA website containing
    the complete NDC directory with product and package information.
    
    Note: The FDA NDC directory is updated regularly. This script
    downloads the latest available version.
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads")
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Downloading NDC Directory" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create download directory
$ndcDir = Join-Path $DownloadDir "ndc"
New-Item -ItemType Directory -Force -Path $ndcDir | Out-Null

# FDA NDC directory URL (update as needed for latest version)
# The FDA provides NDC files at: https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory
# This is a placeholder URL - users should download manually or update with actual API/URL
$ndcUrl = "https://www.fda.gov/media/89850/download"  # Example - update with actual URL

$zipFile = Join-Path $ndcDir "ndctext.zip"

Write-Host "  Source: FDA National Drug Code Directory" -ForegroundColor Yellow
Write-Host "  Target: $zipFile" -ForegroundColor Yellow
Write-Host ""

try {
    # Check if file already exists
    if (Test-Path $zipFile) {
        Write-Host "  File already exists: $zipFile" -ForegroundColor Green
        Write-Host "  To re-download, delete the file first." -ForegroundColor DarkGray
        exit 0
    }

    Write-Host "  Downloading NDC directory..." -ForegroundColor Magenta
    
    # Note: The FDA website may require manual download or have specific access requirements
    # This script provides a template - users may need to download manually
    Write-Host "  WARNING: NDC file download may require manual steps." -ForegroundColor Yellow
    Write-Host "  Please download ndctext.zip from:" -ForegroundColor Yellow
    Write-Host "  https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory" -ForegroundColor Cyan
    Write-Host "  And place it in: $ndcDir" -ForegroundColor Yellow
    Write-Host ""
    
    # Attempt download if URL is valid
    try {
        Invoke-WebRequest -Uri $ndcUrl -OutFile $zipFile -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✓ Download complete: $zipFile" -ForegroundColor Green
    }
    catch {
        Write-Host "  ⚠ Automatic download failed. Please download manually." -ForegroundColor Yellow
        Write-Host "  Error: $_" -ForegroundColor Red
    }
}
catch {
    Write-Host "  ERROR: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  Next step: Run the pipeline to process NDC data:" -ForegroundColor Cyan
Write-Host "    .\scripts\run-pipeline.ps1 -Only ndc" -ForegroundColor DarkGray
