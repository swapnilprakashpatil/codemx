# Generate a custom favicon for the Coding Manager application
# This creates a 32x32 ICO file with a DNA helix theme and transparent background

Add-Type -AssemblyName System.Drawing

# Create a 32x32 bitmap with alpha channel support for transparency
$size = 32
$bitmap = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias

# Make background completely transparent
$graphics.Clear([System.Drawing.Color]::Transparent)

# DNA helix colors - vibrant and clearly visible on transparent background
$strand1Pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(0, 180, 255), 2.8)  # Bright Cyan
$strand2Pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(255, 80, 160), 2.8) # Bright Pink
$basePairPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(200, 200, 200, 200), 1.8) # Light gray

# Draw DNA helix strands as sine waves
$centerX = 16
$amplitude = 6
$frequency = 0.4
$verticalStart = 4
$verticalEnd = 28

# Draw the two strands and connecting base pairs
for ($y = $verticalStart; $y -lt $verticalEnd; $y += 1) {
    $angle = $y * $frequency
    
    # Calculate positions for both strands
    $x1 = $centerX + [Math]::Sin($angle) * $amplitude
    $x2 = $centerX - [Math]::Sin($angle) * $amplitude
    
    # Draw strand points
    if ($y -lt $verticalEnd - 1) {
        $nextAngle = ($y + 1) * $frequency
        $nextX1 = $centerX + [Math]::Sin($nextAngle) * $amplitude
        $nextX2 = $centerX - [Math]::Sin($nextAngle) * $amplitude
        
        $graphics.DrawLine($strand1Pen, $x1, $y, $nextX1, $y + 1)
        $graphics.DrawLine($strand2Pen, $x2, $y, $nextX2, $y + 1)
    }
    
    # Draw base pairs (connecting lines) at specific intervals
    if ($y % 4 -eq 0) {
        $graphics.DrawLine($basePairPen, $x1, $y, $x2, $y)
    }
}

# Clean up
$graphics.Dispose()

# Save as ICO file
$root = Split-Path $PSScriptRoot -Parent
$outputPath = Join-Path $root "frontend\public\favicon.ico"
$icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())

try {
    $fileStream = [System.IO.File]::Create($outputPath)
    $icon.Save($fileStream)
    $fileStream.Close()
    Write-Host "✓ Successfully generated favicon.ico at: $outputPath" -ForegroundColor Green
    Write-Host "  Icon theme: DNA helix with transparent background" -ForegroundColor Cyan
} catch {
    Write-Host "✗ Failed to save favicon: $_" -ForegroundColor Red
} finally {
    $bitmap.Dispose()
    $icon.Dispose()
}
