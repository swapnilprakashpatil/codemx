<#
.SYNOPSIS
    Downloads CPT (Current Procedural Terminology) code data.
.DESCRIPTION
    CPT codes are maintained by the AMA (American Medical Association).
    Due to licensing restrictions, the full CPT dataset requires an AMA license.
    This script provides instructions and downloads freely available Category II/III codes.
.NOTES
    Source: https://www.ama-assn.org/practice-management/cpt
    HCPCS Level I = CPT codes
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
}

Write-Host "=== CPT Code Set Downloader ===" -ForegroundColor Cyan
Write-Host "Download Directory: $DownloadDir"

$extractDir = Join-Path $DownloadDir "cpt"
if (-not (Test-Path $extractDir)) {
    New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
}

Write-Host @"

--- CPT Code Information ---
CPT (Current Procedural Terminology) codes are copyrighted by the AMA.
A license is required to use the full CPT code set.

Steps to obtain CPT codes:
1. Visit: https://www.ama-assn.org/practice-management/cpt
2. Purchase or obtain a license for the CPT code set
3. Download the data files
4. Place the files in: $extractDir

For development purposes, a sample dataset will be created below.

For HCPCS Level II codes (which are freely available), use download_hcpcs.ps1

"@ -ForegroundColor Yellow

# Create sample CPT data for development
$sampleFile = Join-Path $extractDir "sample_cpt_codes.csv"
if (-not (Test-Path $sampleFile)) {
    Write-Host "Creating sample CPT data for development..." -ForegroundColor Yellow

    @"
cpt_code,short_description,long_description,category,status
99201,Office Visit New Low,Office or other outpatient visit for the evaluation and management of a new patient - Level 1,E/M,Active
99202,Office Visit New Straightforward,Office or other outpatient visit for evaluation and management of a new patient requiring straightforward medical decision making,E/M,Active
99203,Office Visit New Low Complexity,Office or other outpatient visit for evaluation and management of a new patient requiring low complexity medical decision making,E/M,Active
99204,Office Visit New Moderate,Office or other outpatient visit for evaluation and management of a new patient requiring moderate complexity medical decision making,E/M,Active
99205,Office Visit New High,Office or other outpatient visit for evaluation and management of a new patient requiring high complexity medical decision making,E/M,Active
99211,Office Visit Est Minimal,Office or other outpatient visit for evaluation and management of an established patient - minimal,E/M,Active
99212,Office Visit Est Straightforward,Office or other outpatient visit for evaluation and management of an established patient requiring straightforward medical decision making,E/M,Active
99213,Office Visit Est Low,Office or other outpatient visit for evaluation and management of an established patient requiring low complexity medical decision making,E/M,Active
99214,Office Visit Est Moderate,Office or other outpatient visit for evaluation and management of an established patient requiring moderate complexity medical decision making,E/M,Active
99215,Office Visit Est High,Office or other outpatient visit for evaluation and management of an established patient requiring high complexity medical decision making,E/M,Active
36415,Venipuncture,Collection of venous blood by venipuncture,Laboratory,Active
36416,Capillary Blood Collection,Collection of capillary blood specimen,Laboratory,Active
71046,Chest X-ray 2 Views,Radiologic examination of chest 2 views,Radiology,Active
71047,Chest X-ray 3 Views,Radiologic examination of chest 3 views,Radiology,Active
80053,Comprehensive Metabolic Panel,Comprehensive metabolic panel,Laboratory,Active
80061,Lipid Panel,Lipid panel,Laboratory,Active
85025,CBC w/ Diff,Complete blood count with automated differential WBC count,Laboratory,Active
93000,ECG 12-Lead,Electrocardiogram routine ECG with at least 12 leads with interpretation and report,Cardiology,Active
93306,Echocardiography TTE,Echocardiography transthoracic real-time with image documentation with complete evaluation,Cardiology,Active
10021,Fine Needle Aspiration,Fine needle aspiration biopsy without imaging guidance,Surgery,Active
"@ | Out-File -FilePath $sampleFile -Encoding utf8

    Write-Host "Sample CPT data created: $sampleFile" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan
