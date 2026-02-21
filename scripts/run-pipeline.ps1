#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Runs the CodeMx data processing pipeline with selectable options.

.DESCRIPTION
    PowerShell wrapper for the CodeMx data pipeline.  Supports running all
    loaders/mappers, individual code systems, validation-only mode, and
    strict error handling.

    Available code-system keys:
      Loaders:   snomed, icd10, hcc, cpt, hcpcs, rxnorm, ndc
      Mappers:   snomed-icd10, icd10-hcc, snomed-hcc, rxnorm-snomed, ndc-rxnorm

.PARAMETER Mode
    Execution mode (default: All).
      All          – run every loader and mapper
      LoadersOnly  – run all loaders, skip mappers
      MappersOnly  – run all mappers, skip loaders
      Select       – interactively pick which systems to run
      Validate     – validate source files only (no data loading)
      Clean        – delete the database only (no reload)
      Reload       – delete the database + run the full pipeline
      Export       – export all datasets to static JSON files

.PARAMETER Only
    Run only these loaders/mappers (space-separated keys).
    Mutually exclusive with -Skip.

.PARAMETER Skip
    Skip these loaders/mappers (space-separated keys).
    Mutually exclusive with -Only.

.PARAMETER Strict
    Abort the pipeline if any validation check fails.

.PARAMETER Clean
    Delete the database before running.  Combines with any mode.
    e.g. -Only cpt -Clean → delete DB then reload CPT only.

.PARAMETER NoOrganize
    Skip Phase 0 file-organisation (staging/archive moves).

.PARAMETER List
    Display available loader/mapper keys and exit.

.EXAMPLE
    .\scripts\run-pipeline.ps1                          # full pipeline
    .\scripts\run-pipeline.ps1 -Mode Validate           # validate sources only
    .\scripts\run-pipeline.ps1 -Only snomed,icd10       # SNOMED + ICD-10 only
    .\scripts\run-pipeline.ps1 -Only cpt -Strict        # CPT only, strict mode
    .\scripts\run-pipeline.ps1 -Skip rxnorm             # everything except RxNorm
    .\scripts\run-pipeline.ps1 -Mode LoadersOnly        # all loaders, no mappers
    .\scripts\run-pipeline.ps1 -Mode Select             # interactive picker
    .\scripts\run-pipeline.ps1 -Mode Clean              # delete database only
    .\scripts\run-pipeline.ps1 -Mode Reload             # delete DB + full reload
    .\scripts\run-pipeline.ps1 -Only cpt -Clean         # delete DB + reload CPT only
    .\scripts\run-pipeline.ps1 -Mode Export             # export JSON for GitHub Pages
    .\scripts\run-pipeline.ps1 -List                    # show available keys
#>

[CmdletBinding()]
param(
    [ValidateSet("All", "LoadersOnly", "MappersOnly", "Select", "Validate", "Clean", "Reload", "Export")]
    [string]$Mode = "All",

    [string[]]$Only,
    [string[]]$Skip,
    [switch]$Strict,
    [switch]$Clean,
    [switch]$NoOrganize,
    [switch]$List
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

# ── Banner ────────────────────────────────────────────────────────────────────
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║   CodeMx - Data Processing Pipeline     ║" -ForegroundColor Cyan
    Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# ── Key definitions ───────────────────────────────────────────────────────────
$LoaderKeys = @("snomed", "icd10", "hcc", "cpt", "hcpcs", "rxnorm", "ndc")
$MapperKeys = @("snomed-icd10", "icd10-hcc", "snomed-hcc", "rxnorm-snomed", "ndc-rxnorm")
$AllKeys    = $LoaderKeys + $MapperKeys

$KeyDescriptions = [ordered]@{
    "snomed"        = "SNOMED CT concepts & descriptions"
    "icd10"         = "ICD-10-CM diagnosis codes"
    "hcc"           = "HCC risk-adjustment categories"
    "cpt"           = "CPT procedure codes (from DHS Code List)"
    "hcpcs"         = "HCPCS Level II codes"
    "rxnorm"        = "RxNorm drug vocabulary"
    "ndc"           = "NDC (National Drug Code) product codes"
    "snomed-icd10"  = "SNOMED CT → ICD-10-CM crosswalk"
    "icd10-hcc"     = "ICD-10-CM → HCC risk mapping"
    "snomed-hcc"    = "SNOMED CT → HCC transitive mapping"
    "rxnorm-snomed" = "RxNorm ↔ SNOMED CT drug mapping"
    "ndc-rxnorm"    = "NDC ↔ RxNorm drug code mapping"
}

# ── List mode ─────────────────────────────────────────────────────────────────
if ($List) {
    Show-Banner
    Write-Host "  Available pipeline keys:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Loaders:" -ForegroundColor Green
    foreach ($k in $LoaderKeys) {
        Write-Host ("    {0,-16} {1}" -f $k, $KeyDescriptions[$k])
    }
    Write-Host ""
    Write-Host "  Mappers:" -ForegroundColor Green
    foreach ($k in $MapperKeys) {
        Write-Host ("    {0,-16} {1}" -f $k, $KeyDescriptions[$k])
    }
    Write-Host ""
    exit 0
}

# ── Validate parameters ──────────────────────────────────────────────────────
if ($Only -and $Skip) {
    Write-Host "  ERROR: -Only and -Skip are mutually exclusive." -ForegroundColor Red
    exit 1
}

# Flatten comma-separated values (e.g. -Only "snomed,icd10")
if ($Only) { $Only = $Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ } }
if ($Skip) { $Skip = $Skip | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ } }

# Validate key names
foreach ($keyList in @($Only, $Skip)) {
    if ($keyList) {
        foreach ($k in $keyList) {
            if ($k -notin $AllKeys) {
                Write-Host "  ERROR: Unknown key '$k'." -ForegroundColor Red
                Write-Host "  Valid keys: $($AllKeys -join ', ')" -ForegroundColor Yellow
                exit 1
            }
        }
    }
}

# ── Interactive Select mode ───────────────────────────────────────────────────
if ($Mode -eq "Select") {
    Show-Banner
    Write-Host "  Select which systems to process:" -ForegroundColor Yellow
    Write-Host "  (Enter numbers separated by commas, or 'a' for all)" -ForegroundColor DarkGray
    Write-Host ""

    $idx = 1
    Write-Host "  Loaders:" -ForegroundColor Green
    foreach ($k in $LoaderKeys) {
        Write-Host ("    [{0}] {1,-16} {2}" -f $idx, $k, $KeyDescriptions[$k])
        $idx++
    }
    Write-Host ""
    Write-Host "  Mappers:" -ForegroundColor Green
    foreach ($k in $MapperKeys) {
        Write-Host ("    [{0}] {1,-16} {2}" -f $idx, $k, $KeyDescriptions[$k])
        $idx++
    }
    Write-Host ""

    $selection = Read-Host "  Selection"
    if ($selection.Trim().ToLower() -eq 'a') {
        $Only = $null  # run all
    } else {
        $nums = $selection -split '[,\s]+' | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }
        if (-not $nums) {
            Write-Host "  No valid selection. Exiting." -ForegroundColor Red
            exit 1
        }
        $Only = @()
        foreach ($n in $nums) {
            if ($n -ge 1 -and $n -le $AllKeys.Count) {
                $Only += $AllKeys[$n - 1]
            } else {
                Write-Host "  WARNING: Ignoring invalid number $n" -ForegroundColor Yellow
            }
        }
        if ($Only.Count -eq 0) {
            Write-Host "  No valid selections. Exiting." -ForegroundColor Red
            exit 1
        }
    }
}

# ── Mode → --only / --skip translation ───────────────────────────────────────
# Clean / Reload modes set the $Clean flag automatically
if ($Mode -eq "Clean" -or $Mode -eq "Reload") {
    $Clean = $true
}

if (-not $Only -and -not $Skip) {
    switch ($Mode) {
        "LoadersOnly" { $Only = $LoaderKeys }
        "MappersOnly" { $Only = $MapperKeys }
        "Validate"    { }  # handled via --validate flag
        "Clean"       { }  # clean-only: handled below
        "Reload"      { }  # clean + full pipeline
    }
}

# ── Build Python command ──────────────────────────────────────────────────────
$pyArgs = @()

if ($Mode -eq "Clean") {
    # Clean-only mode: delete DB and exit (no pipeline run)
    $dbPath = Join-Path $root "backend\data\coding_manager.db"
    Show-Banner
    if (Test-Path $dbPath) {
        Remove-Item $dbPath -Force
        Write-Host "  Database deleted: $dbPath" -ForegroundColor Green
    } else {
        Write-Host "  No database file found — nothing to clean." -ForegroundColor Yellow
    }
    Write-Host ""
    exit 0
}

if ($Mode -eq "Export") {
    # Export mode: generate static JSON files from the database
    Show-Banner
    Write-Host "  Mode:     Export (static JSON for GitHub Pages)" -ForegroundColor Yellow
    Write-Host ""

    Push-Location $root
    try {
        $cmd = "python -m pipeline.export_json"
        Write-Host "  > $cmd" -ForegroundColor DarkGray
        Write-Host ""

        Set-Location (Join-Path $root "backend")
        python -m pipeline.export_json

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "  Export exited with error code $LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }

        Write-Host ""
        Write-Host "  ✓ JSON export completed. Files at: frontend/public/data/" -ForegroundColor Green
        Write-Host ""
    } catch {
        Write-Host ""
        Write-Host "  ERROR: $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
    exit 0
}
if ($Clean) {
    $pyArgs += "--clean"
}
if ($Mode -eq "Validate") {
    $pyArgs += "--validate"
}
if ($Only) {
    $pyArgs += "--only"
    $pyArgs += $Only
}
if ($Skip) {
    $pyArgs += "--skip"
    $pyArgs += $Skip
}
if ($Strict) {
    $pyArgs += "--strict"
}
if ($NoOrganize) {
    $pyArgs += "--no-organize"
}

# ── Show plan ─────────────────────────────────────────────────────────────────
Show-Banner

if ($Mode -eq "Reload") {
    Write-Host "  Mode:     Reload (clean DB + full pipeline)" -ForegroundColor Yellow
} elseif ($Mode -eq "Validate") {
    Write-Host "  Mode:     Validate only" -ForegroundColor Yellow
} elseif ($Clean -and $Only) {
    Write-Host "  Mode:     Clean + reload selected systems" -ForegroundColor Yellow
    Write-Host "  Running:  $($Only -join ', ')" -ForegroundColor Green
} elseif ($Clean) {
    Write-Host "  Mode:     Clean + full reload" -ForegroundColor Yellow
} elseif ($Only) {
    Write-Host "  Mode:     Selected systems" -ForegroundColor Yellow
    Write-Host "  Running:  $($Only -join ', ')" -ForegroundColor Green
} elseif ($Skip) {
    Write-Host "  Mode:     All except skipped" -ForegroundColor Yellow
    Write-Host "  Skipping: $($Skip -join ', ')" -ForegroundColor DarkYellow
} else {
    Write-Host "  Mode:     Full pipeline (all loaders + mappers)" -ForegroundColor Yellow
}

if ($Strict)    { Write-Host "  Strict:   ON — abort on validation failure" -ForegroundColor Red }
if ($NoOrganize){ Write-Host "  Organize: SKIPPED" -ForegroundColor DarkYellow }
Write-Host ""

# ── Execute ───────────────────────────────────────────────────────────────────
Push-Location $root
try {
    $cmd = "python -m pipeline.pipeline $($pyArgs -join ' ')"
    Write-Host "  > $cmd" -ForegroundColor DarkGray
    Write-Host ""

    Set-Location (Join-Path $root "backend")
    python -m pipeline.pipeline @pyArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  Pipeline exited with error code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "  ✓ Pipeline completed successfully." -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host ""
    Write-Host "  ERROR: $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}
