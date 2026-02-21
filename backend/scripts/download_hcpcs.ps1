<#
.SYNOPSIS
    Downloads HCPCS Level II code set from CMS.
.DESCRIPTION
    Downloads the Healthcare Common Procedure Coding System (HCPCS) Level II codes.
    These are maintained by CMS and are freely available.
.NOTES
    Source: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads"),
    [int]$Year = 2026
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
}

Write-Host "=== HCPCS Level II Code Set Downloader ===" -ForegroundColor Cyan
Write-Host "Year: $Year"
Write-Host "Download Directory: $DownloadDir"

# CMS HCPCS page: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
# Correct pattern: january-{YEAR}-alpha-numeric-hcpcs-file.zip
$baseUrl = "https://www.cms.gov/files/zip"
$fileName = "january-$Year-alpha-numeric-hcpcs-file.zip"
$url = "$baseUrl/$fileName"
$outputPath = Join-Path $DownloadDir $fileName
$extractDir = Join-Path $DownloadDir "hcpcs"

try {
    Write-Host "`nDownloading HCPCS from: $url" -ForegroundColor Yellow

    if (Test-Path $outputPath) {
        Write-Host "File already exists. Skipping download." -ForegroundColor Green
    } else {
        Invoke-WebRequest -Uri $url -OutFile $outputPath -UseBasicParsing
        Write-Host "Download complete: $outputPath" -ForegroundColor Green
    }

    if (-not (Test-Path $extractDir)) {
        New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
    }

    Write-Host "Extracting to: $extractDir" -ForegroundColor Yellow
    Expand-Archive -Path $outputPath -DestinationPath $extractDir -Force
    Write-Host "Extraction complete." -ForegroundColor Green

    Get-ChildItem -Path $extractDir -Recurse | ForEach-Object {
        Write-Host "  $($_.FullName)"
    }
}
catch {
    Write-Error "Failed to download HCPCS: $_"

    Write-Host "`n--- Manual Download Instructions ---" -ForegroundColor Yellow
    Write-Host "1. Visit: https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system"
    Write-Host "2. Download the Alpha-Numeric HCPCS file for $Year"
    Write-Host "3. Extract contents to: $extractDir"
}

# Create sample HCPCS data for development
$sampleFile = Join-Path $extractDir "sample_hcpcs_codes.csv"
if (-not (Test-Path $sampleFile)) {
    if (-not (Test-Path $extractDir)) {
        New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
    }
    
    Write-Host "`nCreating sample HCPCS data for development..." -ForegroundColor Yellow

    @"
hcpcs_code,short_description,long_description,category,status
A0021,Ambulance Oxygen,Ambulance service outside state per loaded miles,Transportation,Active
A0425,Ground Mileage,Ground mileage per statute mile,Transportation,Active
A4206,Syringe with Needle,Syringe with needle sterile 1 cc or less each,Supplies,Active
A4253,Blood Glucose Test Strip,Blood glucose test or reagent strips for home blood glucose monitor per 50 strips,Supplies,Active
A4550,Surgical Trays,Surgical trays,Supplies,Active
A4649,Surgical Supply Misc,Surgical supply miscellaneous,Supplies,Active
B4034,Enteral Feeding Supply,Enteral feeding supply kit syringe per day,Enteral/Parenteral,Active
E0260,Hospital Bed Semi-Electric,Hospital bed semi-electric (head and foot adjustment) with any type side rails with mattress,DME,Active
E0601,CPAP Device,Continuous positive airway pressure (CPAP) device,DME,Active
G0008,Admin Influenza Virus Vac,Administration of influenza virus vaccine,Temporary,Active
G0101,Cervical/Vaginal Screening,Cervical or vaginal cancer screening pelvic and clinical breast examination,Temporary,Active
G0108,Diabetes Mgmt Training,Diabetes outpatient self-management training services individual per 30 minutes,Temporary,Active
J0585,Botulinum Toxin A,Injection onabotulinumtoxinA 1 unit,Drugs,Active
J1100,Dexamethasone Sodium,Injection dexamethasone sodium phosphate 1 mg,Drugs,Active
J2001,Lidocaine Injection,Injection lidocaine HCl for intravenous infusion 10 mg,Drugs,Active
K0001,Standard Wheelchair,Standard wheelchair,DME,Active
L0120,Cervical Collar,Cervical flexible non-adjustable molded chin support prefabricated,Orthotics,Active
Q0081,Infusion Therapy,Infusion therapy using other than chemotherapeutic drugs per visit,Temporary,Active
S0390,Routine Foot Care,Routine foot care removal and/or trimming of corns calluses and/or nails,Temporary,Active
V2020,Frames Purchases,Frames purchases,Vision,Active
"@ | Out-File -FilePath $sampleFile -Encoding utf8

    Write-Host "Sample HCPCS data created: $sampleFile" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan
