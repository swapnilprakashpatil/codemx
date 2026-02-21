#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Starts the CodeMx Medical Coding Manager (backend + frontend).

.DESCRIPTION
    Launches the Flask API server (port 5000) and the Angular dev server
    with watch mode (port 4200), then opens the app in the default browser.
    Press Ctrl+C to stop both servers.
#>

param(
    [int]$BackendPort  = 5000,
    [int]$FrontendPort = 4200,
    [switch]$NoBrowser,
    [switch]$StaticMode
)

$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║       CodeMx - Starting Servers      ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($StaticMode) {
    Write-Host "  [MODE] Running in Static mode (browser-based database)" -ForegroundColor Magenta
    Write-Host ""
}

# ── Ensure database exists ───────────────────────────────────────────────────
if ($StaticMode) {
    # Check for browser database (compressed version preferred)
    $browserDbGzPath = Join-Path $root "frontend\public\data\coding_database.sqlite.gz"
    $browserDbPath = Join-Path $root "frontend\public\data\coding_database.sqlite"
    
    if (-not (Test-Path $browserDbGzPath)) {
        Write-Host "  [BUILD] Compressed browser database not found. Generating from backend database..." -ForegroundColor Yellow
        $backendDbPath = Join-Path $root "backend\data\coding_manager.db"
        if (-not (Test-Path $backendDbPath)) {
            Write-Host "  [BUILD] ✗ Backend database not found. Please run the data pipeline first." -ForegroundColor Red
            Write-Host "  [BUILD] Run: python -m backend.pipeline.process_data" -ForegroundColor Gray
            exit 1
        }
        Write-Host "  [BUILD] Exporting and compressing database for browser use..." -ForegroundColor Gray
        Push-Location $root
        python -m backend.pipeline.export_sqlite_browser --compress
        $exportResult = $LASTEXITCODE
        Pop-Location
        if ($exportResult -ne 0) {
            Write-Host "  [BUILD] ✗ Database export failed with exit code $exportResult" -ForegroundColor Red
            exit 1
        }
        Write-Host "  [BUILD] ✓ Browser database created and compressed successfully." -ForegroundColor Green
    } else {
        Write-Host "  [BUILD] ✓ Compressed browser database found." -ForegroundColor Green
    }
} else {
    # Check for backend database
    $dbPath = Join-Path $root "backend\data\coding_manager.db"
    if (-not (Test-Path $dbPath)) {
    Write-Host "  [BUILD] Database not found. Running data pipeline..." -ForegroundColor Yellow
    Write-Host "  [BUILD] This may take a few minutes..." -ForegroundColor Gray
    Push-Location $root
    python -m backend.pipeline.process_data
    $buildResult = $LASTEXITCODE
    Pop-Location
    if ($buildResult -ne 0) {
        Write-Host ""
        Write-Host "  [BUILD] ✗ Data pipeline failed with exit code $buildResult" -ForegroundColor Red
        Write-Host "  [BUILD] Please check the error messages above." -ForegroundColor Red
        exit 1
    }
        Write-Host "  [BUILD] ✓ Database created successfully." -ForegroundColor Green
    } else {
        Write-Host "  [BUILD] ✓ Database found." -ForegroundColor Green
    }
}

# Store process IDs for cleanup
$script:backendProcess = $null
$script:frontendProcess = $null

# Cleanup function
function Stop-Servers {
    Write-Host ""
    Write-Host "  [STOP] Shutting down servers..." -ForegroundColor Yellow
    
    if ($script:backendProcess -and -not $script:backendProcess.HasExited) {
        Write-Host "  [STOP] Stopping backend..." -ForegroundColor Gray
        Stop-Process -Id $script:backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    if ($script:frontendProcess -and -not $script:frontendProcess.HasExited) {
        Write-Host "  [STOP] Stopping frontend..." -ForegroundColor Gray
        Stop-Process -Id $script:frontendProcess.Id -Force -ErrorAction SilentlyContinue
        
        # Also kill any child node processes
        Get-Process node -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*ng serve*" -or $_.CommandLine -like "*@angular*"
        } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "  [STOP] ✓ All servers stopped." -ForegroundColor Green
}

# Register cleanup on exit
Register-EngineEvent PowerShell.Exiting -Action { Stop-Servers } | Out-Null

# ── Start Flask backend ──────────────────────────────────────────────────────
if (-not $StaticMode) {
Write-Host "  [API] Starting Flask backend on port $BackendPort..." -ForegroundColor Cyan

$backendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$backendStartInfo.FileName = "python"
$backendStartInfo.Arguments = "backend/api/app.py"
$backendStartInfo.WorkingDirectory = $root
$backendStartInfo.UseShellExecute = $false
$backendStartInfo.RedirectStandardOutput = $true
$backendStartInfo.RedirectStandardError = $true
$backendStartInfo.CreateNoWindow = $true
$backendStartInfo.EnvironmentVariables["PYTHONPATH"] = $root

$script:backendProcess = New-Object System.Diagnostics.Process
$script:backendProcess.StartInfo = $backendStartInfo

# Capture output asynchronously
$backendOutput = New-Object System.Collections.Concurrent.ConcurrentQueue[string]
$backendErrors = New-Object System.Collections.Concurrent.ConcurrentQueue[string]

Register-ObjectEvent -InputObject $script:backendProcess -EventName OutputDataReceived -Action {
    if ($EventArgs.Data) {
        $Event.MessageData.Enqueue($EventArgs.Data)
    }
} -MessageData $backendOutput | Out-Null

Register-ObjectEvent -InputObject $script:backendProcess -EventName ErrorDataReceived -Action {
    if ($EventArgs.Data) {
        $Event.MessageData.Enqueue($EventArgs.Data)
    }
} -MessageData $backendErrors | Out-Null

$script:backendProcess.Start() | Out-Null
$script:backendProcess.BeginOutputReadLine()
$script:backendProcess.BeginErrorReadLine()

# Wait for backend to be ready
Write-Host "  [API] Waiting for backend to start..." -ForegroundColor Gray

# Give it a moment to initialize the database
Start-Sleep -Milliseconds 1500

$backendReady = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Milliseconds 500
    
    # Show any output
    while ($backendOutput.TryDequeue([ref]$null)) {
        $line = $null
        if ($backendOutput.TryDequeue([ref]$line)) {
            Write-Host "  [API] $line" -ForegroundColor DarkCyan
        }
    }
    
    # Show any errors
    while ($backendErrors.TryDequeue([ref]$null)) {
        $err = $null
        if ($backendErrors.TryDequeue([ref]$err)) {
            Write-Host "  [API] $err" -ForegroundColor Red
        }
    }
    
    # Check if process died
    if ($script:backendProcess.HasExited) {
        Write-Host "  [API] ✗ Backend process exited with code $($script:backendProcess.ExitCode)" -ForegroundColor Red
        exit 1
    }
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/api/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $backendReady = $true
        break
    } catch {
        # Not ready yet - show error on first and every 10th attempt
        if ($i -eq 0 -or $i % 10 -eq 0) {
            Write-Host "  [API] Health check attempt $($i+1): $($_.Exception.Message)" -ForegroundColor DarkGray
        }
    }
}

if ($backendReady) {
    Write-Host "  [API] ✓ Backend ready at http://localhost:$BackendPort" -ForegroundColor Green
} else {
    Write-Host "  [API] ✗ Backend failed to start within 30 seconds" -ForegroundColor Red
    Stop-Servers
    exit 1
}
} else {
    Write-Host "  [API] Skipping backend (static mode)" -ForegroundColor Gray
}

# ── Start Angular frontend ───────────────────────────────────────────────────
Write-Host "  [WEB] Starting Angular dev server on port $FrontendPort..." -ForegroundColor Cyan
Write-Host "  [WEB] Initial build and compilation starting (watch mode enabled)..." -ForegroundColor Gray

$frontendStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$frontendStartInfo.FileName = "cmd.exe"
$ngServeArgs = "--port $FrontendPort --watch"
if ($StaticMode) {
    $ngServeArgs += " --configuration=static"
    Write-Host "  [WEB] Running with --configuration=static" -ForegroundColor Magenta
}
Write-Host "  [DEBUG] Command: ng serve $ngServeArgs" -ForegroundColor DarkGray
$frontendStartInfo.Arguments = "/c cd /d `"$(Join-Path $root 'frontend')`" && npx ng serve $ngServeArgs"
$frontendStartInfo.WorkingDirectory = $root
$frontendStartInfo.UseShellExecute = $false
$frontendStartInfo.RedirectStandardOutput = $true
$frontendStartInfo.RedirectStandardError = $true
$frontendStartInfo.CreateNoWindow = $true

$script:frontendProcess = New-Object System.Diagnostics.Process
$script:frontendProcess.StartInfo = $frontendStartInfo

# Capture output asynchronously
$frontendOutput = New-Object System.Collections.Concurrent.ConcurrentQueue[string]
$frontendErrors = New-Object System.Collections.Concurrent.ConcurrentQueue[string]

Register-ObjectEvent -InputObject $script:frontendProcess -EventName OutputDataReceived -Action {
    if ($EventArgs.Data) {
        $Event.MessageData.Enqueue($EventArgs.Data)
    }
} -MessageData $frontendOutput | Out-Null

Register-ObjectEvent -InputObject $script:frontendProcess -EventName ErrorDataReceived -Action {
    if ($EventArgs.Data) {
        $Event.MessageData.Enqueue($EventArgs.Data)
    }
} -MessageData $frontendErrors | Out-Null

$script:frontendProcess.Start() | Out-Null
$script:frontendProcess.BeginOutputReadLine()
$script:frontendProcess.BeginErrorReadLine()

# Wait for Angular to compile - show build output
$frontendReady = $false
$compilationErrors = @()
$showedCompileStart = $false

for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Milliseconds 1000
    
    # Show frontend output
    while ($frontendOutput.TryDequeue([ref]$null)) {
        $line = $null
        if ($frontendOutput.TryDequeue([ref]$line)) {
            if ($line -match "ERROR|TS\d+:|error TS") {
                Write-Host "  [WEB] $line" -ForegroundColor Red
                $compilationErrors += $line
            } elseif ($line -match "WARNING|warning") {
                Write-Host "  [WEB] $line" -ForegroundColor Yellow
            } elseif ($line -match "Application bundle generation complete|Compiled successfully|Local:.*http") {
                Write-Host "  [WEB] $line" -ForegroundColor Green
            } elseif ($line -match "compiling|building|bundle") {
                if (-not $showedCompileStart) {
                    Write-Host "  [WEB] $line" -ForegroundColor Gray
                    $showedCompileStart = $true
                }
            }
        }
    }
    
    # Show frontend errors
    while ($frontendErrors.TryDequeue([ref]$null)) {
        $err = $null
        if ($frontendErrors.TryDequeue([ref]$err)) {
            Write-Host "  [WEB] $err" -ForegroundColor Red
            $compilationErrors += $err
        }
    }
    
    # Check if process died
    if ($script:frontendProcess.HasExited) {
        Write-Host "  [WEB] ✗ Frontend process exited with code $($script:frontendProcess.ExitCode)" -ForegroundColor Red
        if ($compilationErrors.Count -gt 0) {
            Write-Host ""
            Write-Host "  [WEB] Compilation errors detected:" -ForegroundColor Red
            $compilationErrors | ForEach-Object { Write-Host "       $_" -ForegroundColor Red }
        }
        Stop-Servers
        exit 1
    }
    
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:$FrontendPort" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $frontendReady = $true
        break
    } catch {
        # Not ready yet
    }
}

if ($frontendReady) {
    Write-Host "  [WEB] ✓ Frontend ready at http://localhost:$FrontendPort" -ForegroundColor Green
    if ($compilationErrors.Count -gt 0) {
        Write-Host "  [WEB] ⚠ Built with errors/warnings - check output above" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [WEB] ✗ Frontend failed to start within 90 seconds" -ForegroundColor Red
    if ($compilationErrors.Count -gt 0) {
        Write-Host ""
        Write-Host "  [WEB] Compilation errors:" -ForegroundColor Red
        $compilationErrors | ForEach-Object { Write-Host "       $_" -ForegroundColor Red }
    }
    Stop-Servers
    exit 1
}

# ── Open browser ─────────────────────────────────────────────────────────────
if (-not $NoBrowser) {
    Write-Host "  [APP] Opening browser..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500
    Start-Process "http://localhost:$FrontendPort"
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║         CodeMx is running!           ║" -ForegroundColor Green
Write-Host "  ║                                      ║" -ForegroundColor Green
Write-Host "  ║  Frontend: http://localhost:$FrontendPort     ║" -ForegroundColor Green
if (-not $StaticMode) {
Write-Host "  ║  Backend:  http://localhost:$BackendPort      ║" -ForegroundColor Green
} else {
Write-Host "  ║  Mode:     Static (browser database) ║" -ForegroundColor Green
}
Write-Host "  ║                                      ║" -ForegroundColor Green
Write-Host "  ║  Watching for file changes...        ║" -ForegroundColor Green
Write-Host "  ║  Press Ctrl+C to stop all servers    ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Tail logs until Ctrl+C ───────────────────────────────────────────────────
try {
    while ($true) {
        # Stream backend output (if running)
        if (-not $StaticMode) {
            while ($backendOutput.TryDequeue([ref]$null)) {
                $line = $null
                if ($backendOutput.TryDequeue([ref]$line)) {
                    Write-Host "  [API] $line" -ForegroundColor DarkCyan
                }
            }
            
            # Stream backend errors
            while ($backendErrors.TryDequeue([ref]$null)) {
                $err = $null
                if ($backendErrors.TryDequeue([ref]$err)) {
                    if ($err -match "ERROR|Exception|Traceback") {
                        Write-Host "  [API] $err" -ForegroundColor Red
                    } else {
                        Write-Host "  [API] $err" -ForegroundColor Yellow
                    }
                }
            }
        }

        # Stream frontend output (only important messages after startup)
        while ($frontendOutput.TryDequeue([ref]$null)) {
            $line = $null
            if ($frontendOutput.TryDequeue([ref]$line)) {
                if ($line -match "ERROR|TS\d+:|error TS|Exception") {
                    Write-Host "  [WEB] $line" -ForegroundColor Red
                } elseif ($line -match "WARNING|warning") {
                    Write-Host "  [WEB] $line" -ForegroundColor Yellow
                } elseif ($line -match "compiled|changes detected|recompiling|Application bundle generation complete") {
                    Write-Host "  [WEB] $line" -ForegroundColor Cyan
                }
            }
        }
        
        # Stream frontend errors
        while ($frontendErrors.TryDequeue([ref]$null)) {
            $err = $null
            if ($frontendErrors.TryDequeue([ref]$err)) {
                Write-Host "  [WEB] $err" -ForegroundColor Red
            }
        }

        # Check if processes died
        if (-not $StaticMode -and $script:backendProcess.HasExited) {
            Write-Host "  [API] ✗ Backend crashed with exit code $($script:backendProcess.ExitCode)!" -ForegroundColor Red
            break
        }
        if ($script:frontendProcess.HasExited) {
            Write-Host "  [WEB] ✗ Frontend crashed with exit code $($script:frontendProcess.ExitCode)!" -ForegroundColor Red
            break
        }

        Start-Sleep -Milliseconds 500
    }
} finally {
    Stop-Servers
}
