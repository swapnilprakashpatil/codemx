<#
.SYNOPSIS
    Master script to download all coding sets.
.DESCRIPTION
    Runs all download scripts in sequence to obtain ICD-10-CM, HCC, SNOMED, CPT, and HCPCS data.
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads")
)

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Coding Manager - Download All Datasets" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scripts = @(
    @{ Name = "ICD-10-CM"; Script = "download_icd10cm.ps1" },
    @{ Name = "HCC";       Script = "download_hcc.ps1" },
    @{ Name = "SNOMED CT"; Script = "download_snomed.ps1" },
    @{ Name = "CPT";       Script = "download_cpt.ps1" },
    @{ Name = "HCPCS";     Script = "download_hcpcs.ps1" },
    @{ Name = "NDC";       Script = "download_ndc.ps1" }
)

foreach ($item in $scripts) {
    Write-Host "`n--- Downloading $($item.Name) ---" -ForegroundColor Magenta
    $scriptPath = Join-Path $PSScriptRoot $item.Script
    
    try {
        & $scriptPath -DownloadDir $DownloadDir
    }
    catch {
        Write-Warning "Failed to run $($item.Script): $_"
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  All Downloads Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext steps:"
Write-Host "  1. Review downloaded files in: $DownloadDir"
Write-Host "  2. Run the Python data processing pipeline:"
Write-Host "     python backend/pipeline/process_data.py"
Write-Host "  3. Start the Flask API:"
Write-Host "     python backend/api/app.py"
