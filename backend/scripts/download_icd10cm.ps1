<#
.SYNOPSIS
    Downloads the latest ICD-10-CM code set from CMS.gov.
.DESCRIPTION
    Downloads the ICD-10-CM tabular data (order file) from the CMS website.
    The data is saved to the backend/data/downloads directory.
.NOTES
    Source: https://www.cms.gov/medicare/coding-billing/icd-10-codes
    Updated annually (typically effective October 1st each fiscal year).
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads"),
    [int]$FiscalYear = 2026
)

$ErrorActionPreference = "Stop"

# Ensure download directory exists
if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
}

Write-Host "=== ICD-10-CM Code Set Downloader ===" -ForegroundColor Cyan
Write-Host "Fiscal Year: $FiscalYear"
Write-Host "Download Directory: $DownloadDir"

# CMS publishes ICD-10-CM files at predictable URLs
# Correct pattern: {YEAR}-code-descriptions-tabular-order.zip
$baseUrl = "https://www.cms.gov/files/zip"
$fileName = "$FiscalYear-code-descriptions-tabular-order.zip"
$url = "$baseUrl/$fileName"
$outputPath = Join-Path $DownloadDir $fileName
$extractDir = Join-Path $DownloadDir "icd10cm"

try {
    Write-Host "`nDownloading ICD-10-CM from: $url" -ForegroundColor Yellow
    
    if (Test-Path $outputPath) {
        Write-Host "File already exists. Skipping download." -ForegroundColor Green
    } else {
        Invoke-WebRequest -Uri $url -OutFile $outputPath -UseBasicParsing
        Write-Host "Download complete: $outputPath" -ForegroundColor Green
    }

    # Extract
    if (-not (Test-Path $extractDir)) {
        New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
    }
    
    Write-Host "Extracting to: $extractDir" -ForegroundColor Yellow
    Expand-Archive -Path $outputPath -DestinationPath $extractDir -Force
    Write-Host "Extraction complete." -ForegroundColor Green

    # List extracted files
    Write-Host "`nExtracted files:" -ForegroundColor Cyan
    Get-ChildItem -Path $extractDir -Recurse | ForEach-Object {
        Write-Host "  $($_.FullName)"
    }
}
catch {
    Write-Error "Failed to download ICD-10-CM: $_"
    
    # Provide fallback instructions
    Write-Host "`n--- Manual Download Instructions ---" -ForegroundColor Yellow
    Write-Host "1. Visit: https://www.cms.gov/medicare/coding-billing/icd-10-codes"
    Write-Host "2. Download the latest ICD-10-CM Tabular Order file"
    Write-Host "3. Extract the ZIP contents to: $extractDir"
    Write-Host "4. Ensure the .txt order file is in the extracted directory"
}

Write-Host "`nDone." -ForegroundColor Cyan
