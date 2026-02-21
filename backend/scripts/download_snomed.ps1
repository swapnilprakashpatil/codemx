<#
.SYNOPSIS
    Downloads SNOMED CT to ICD-10-CM mapping files from NLM/IHTSDO.
.DESCRIPTION
    Downloads the official SNOMED CT to ICD-10-CM mapping released by NLM (National Library of Medicine).
    This mapping is critical for translating clinical terminology (SNOMED) to billing codes (ICD-10-CM).
.NOTES
    Source: https://www.nlm.nih.gov/healthit/snomedct/us_edition.html
    UMLS License required for download - instructions provided for manual download.
    The SNOMED CT International Edition maps are from: https://www.snomed.org/
#>

param(
    [string]$DownloadDir = (Join-Path $PSScriptRoot "..\data\downloads"),
    [string]$Edition = "US1000124_20250301"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $DownloadDir)) {
    New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
}

Write-Host "=== SNOMED CT Mapping Downloader ===" -ForegroundColor Cyan
Write-Host "Edition: $Edition"
Write-Host "Download Directory: $DownloadDir"

$extractDir = Join-Path $DownloadDir "snomed"

# SNOMED CT requires a UMLS license for download.
# We provide instructions and check for pre-placed files.
Write-Host "`n--- SNOMED CT Download Instructions ---" -ForegroundColor Yellow
Write-Host @"
SNOMED CT data requires a free UMLS license from NLM.

Steps to obtain SNOMED CT to ICD-10-CM mappings:

1. Register for a UMLS license at: https://uts.nlm.nih.gov/uts/
2. Log in to the UMLS download portal
3. Download the following files:
   a. SNOMED CT US Edition (Full Release)
      - Contains: Concept, Description, and Relationship files
   b. SNOMED CT to ICD-10-CM Map
      - File: tls_Icd10cmHumanReadableMap_${Edition}.tsv
      - Or from: https://download.nlm.nih.gov/mlb/utsauth/USExt/

4. Place the downloaded ZIP files in: $DownloadDir
5. Re-run this script to extract them.

Alternative: Use the SNOMED CT Browser API for on-demand lookups:
   https://browser.ihtsdotools.org/snowstorm/snomed-ct/

For the mapping file specifically:
   - The map file is typically named: der2_iisssccRefset_ExtendedMapFull_US1000124_*.txt
   - Place it in: $extractDir
"@ 

if (-not (Test-Path $extractDir)) {
    New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
}

# Check if files have been manually placed
$snomedFiles = Get-ChildItem -Path $DownloadDir -Filter "SnomedCT_*.zip" -ErrorAction SilentlyContinue
$mapFiles = Get-ChildItem -Path $DownloadDir -Filter "*ICD10*Map*.zip" -ErrorAction SilentlyContinue

if ($snomedFiles -or $mapFiles) {
    Write-Host "`nFound SNOMED files to extract:" -ForegroundColor Green
    
    foreach ($file in @($snomedFiles) + @($mapFiles)) {
        if ($null -ne $file) {
            Write-Host "  Extracting: $($file.Name)" -ForegroundColor Yellow
            Expand-Archive -Path $file.FullName -DestinationPath $extractDir -Force
        }
    }
    
    Write-Host "Extraction complete." -ForegroundColor Green
} else {
    Write-Host "`nNo SNOMED files found in $DownloadDir" -ForegroundColor Red
    Write-Host "Please download the files manually and place them in the directory above."
}

# Also create a sample/seed data file for development
$sampleFile = Join-Path $extractDir "sample_snomed_icd10_map.csv"
if (-not (Test-Path $sampleFile)) {
    Write-Host "`nCreating sample mapping data for development..." -ForegroundColor Yellow
    
    @"
id,effectiveTime,active,moduleId,refsetId,referencedComponentId,referencedComponentName,mapGroup,mapPriority,mapRule,mapAdvice,mapTarget,mapTargetName,correlationId,mapCategoryId
1,20250301,1,449080006,6011000124106,22298006,Myocardial infarction,1,1,TRUE,ALWAYS I21.9,I21.9,Acute myocardial infarction unspecified,447561005,447637006
2,20250301,1,449080006,6011000124106,73211009,Diabetes mellitus,1,1,TRUE,ALWAYS E11.9,E11.9,Type 2 diabetes mellitus without complications,447561005,447637006
3,20250301,1,449080006,6011000124106,38341003,Hypertensive disorder,1,1,TRUE,ALWAYS I10,I10,Essential (primary) hypertension,447561005,447637006
4,20250301,1,449080006,6011000124106,195967001,Asthma,1,1,TRUE,ALWAYS J45.909,J45.909,Unspecified asthma uncomplicated,447561005,447637006
5,20250301,1,449080006,6011000124106,13645005,Chronic obstructive lung disease,1,1,TRUE,ALWAYS J44.1,J44.1,Chronic obstructive pulmonary disease with acute exacerbation,447561005,447637006
6,20250301,1,449080006,6011000124106,40930008,Hypothyroidism,1,1,TRUE,ALWAYS E03.9,E03.9,Hypothyroidism unspecified,447561005,447637006
7,20250301,1,449080006,6011000124106,84114007,Heart failure,1,1,TRUE,ALWAYS I50.9,I50.9,Heart failure unspecified,447561005,447637006
8,20250301,1,449080006,6011000124106,49436004,Atrial fibrillation,1,1,TRUE,ALWAYS I48.91,I48.91,Unspecified atrial fibrillation,447561005,447637006
9,20250301,1,449080006,6011000124106,431855005,Chronic kidney disease stage 3,1,1,TRUE,ALWAYS N18.3,N18.3,Chronic kidney disease stage 3 (moderate),447561005,447637006
10,20250301,1,449080006,6011000124106,267036007,Dyspnea,1,1,TRUE,ALWAYS R06.00,R06.00,Dyspnea unspecified,447561005,447637006
11,20250301,1,449080006,6011000124106,44054006,Type 2 diabetes mellitus,1,1,TRUE,ALWAYS E11.9,E11.9,Type 2 diabetes mellitus without complications,447561005,447637006
12,20250301,1,449080006,6011000124106,46635009,Type 1 diabetes mellitus,1,1,TRUE,ALWAYS E10.9,E10.9,Type 1 diabetes mellitus without complications,447561005,447637006
13,20250301,1,449080006,6011000124106,233604007,Pneumonia,1,1,TRUE,ALWAYS J18.9,J18.9,Pneumonia unspecified organism,447561005,447637006
14,20250301,1,449080006,6011000124106,25064002,Headache,1,1,TRUE,ALWAYS R51.9,R51.9,Headache unspecified,447561005,447637006
15,20250301,1,449080006,6011000124106,386661006,Fever,1,1,TRUE,ALWAYS R50.9,R50.9,Fever unspecified,447561005,447637006
16,20250301,1,449080006,6011000124106,267102003,Sore throat symptom,1,1,TRUE,ALWAYS J02.9,J02.9,Acute pharyngitis unspecified,447561005,447637006
17,20250301,1,449080006,6011000124106,36971009,Sinusitis,1,1,TRUE,ALWAYS J32.9,J32.9,Chronic sinusitis unspecified,447561005,447637006
18,20250301,1,449080006,6011000124106,68566005,Urinary tract infection,1,1,TRUE,ALWAYS N39.0,N39.0,Urinary tract infection site not specified,447561005,447637006
19,20250301,1,449080006,6011000124106,398254007,Pre-eclampsia,1,1,TRUE,ALWAYS O14.90,O14.90,Unspecified pre-eclampsia unspecified trimester,447561005,447637006
20,20250301,1,449080006,6011000124106,371631005,Transcutaneous oxygen monitoring,1,1,TRUE,ALWAYS Z13.83,Z13.83,Encounter for screening for respiratory disorder NEC,447561005,447637006
"@ | Out-File -FilePath $sampleFile -Encoding utf8
    
    Write-Host "Sample mapping file created: $sampleFile" -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Cyan
