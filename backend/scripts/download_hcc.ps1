<#
.SYNOPSIS
    Downloads the HCC (Hierarchical Condition Category) risk adjustment model files from CMS.
.DESCRIPTION
    Downloads the HCC crosswalk / risk adjustment model mappings.
    HCC codes map from ICD-10-CM diagnosis codes to HCC categories.
.NOTES
    Source: https://www.cms.gov/medicare/health-plans/medicareadvtgspecratestats/risk-adjustors
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads"),
    [int]$PaymentYear = 2026
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
}

Write-Host "=== HCC Risk Adjustment Model Downloader ===" -ForegroundColor Cyan
Write-Host "Payment Year: $PaymentYear"
Write-Host "Download Directory: $DownloadDir"

# CMS Risk Adjustment page: https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment
# Sub-page: {YEAR}-model-software-icd-10-mappings
$baseUrl = "https://www.cms.gov/files/zip"

# Download both ICD-10-CM mappings and model software
$mappingsFile = "$PaymentYear-initial-icd-10-cm-mappings.zip"
$softwareFile = "$PaymentYear-initial-model-software.zip"
$midyearFile = "$PaymentYear-midyear-final-icd-10-mappings.zip"
$fileName = $mappingsFile
$url = "$baseUrl/$fileName"
$outputPath = Join-Path $DownloadDir $fileName
$extractDir = Join-Path $DownloadDir "hcc"

if (-not (Test-Path $extractDir)) {
    New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
}

# Download all available HCC files
$filesToDownload = @(
    @{ Name = "Initial ICD-10-CM Mappings"; File = $mappingsFile },
    @{ Name = "Initial Model Software"; File = $softwareFile },
    @{ Name = "Midyear/Final ICD-10 Mappings"; File = $midyearFile }
)

$downloadedAny = $false
foreach ($item in $filesToDownload) {
    $dlUrl = "$baseUrl/$($item.File)"
    $dlPath = Join-Path $DownloadDir $item.File
    
    try {
        Write-Host "`nDownloading $($item.Name) from: $dlUrl" -ForegroundColor Yellow

        if (Test-Path $dlPath) {
            Write-Host "File already exists. Skipping download." -ForegroundColor Green
        } else {
            Invoke-WebRequest -Uri $dlUrl -OutFile $dlPath -UseBasicParsing
            Write-Host "Download complete: $dlPath" -ForegroundColor Green
        }

        Write-Host "Extracting to: $extractDir" -ForegroundColor Yellow
        Expand-Archive -Path $dlPath -DestinationPath $extractDir -Force
        Write-Host "Extraction complete." -ForegroundColor Green
        $downloadedAny = $true
    }
    catch {
        Write-Host "Could not download $($item.Name): $_" -ForegroundColor DarkYellow
    }
}

if ($downloadedAny) {
    Write-Host "`nExtracted files:" -ForegroundColor Cyan
    Get-ChildItem -Path $extractDir -Recurse | ForEach-Object {
        Write-Host "  $($_.FullName)"
    }
} else {
    Write-Host "`n--- Manual Download Instructions ---" -ForegroundColor Yellow
    Write-Host "1. Visit: https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics/risk-adjustment/$PaymentYear-model-software-icd-10-mappings"
    Write-Host "2. Download the ICD-10-CM to HCC mapping files"
    Write-Host "3. Extract contents to: $extractDir"
}

Write-Host "`nDone." -ForegroundColor Cyan
