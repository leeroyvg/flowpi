$ErrorActionPreference = "Stop"

Write-Host "Starting Flow System..."

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $baseDir

$venvPython = Join-Path $baseDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python is not available. Create/activate a .venv or install Python first."
    }
    $pythonExe = $pythonCommand.Source
}

if (-not $env:FLOWPI_HOST) { $env:FLOWPI_HOST = "0.0.0.0" }
if (-not $env:FLOWPI_PORT) { $env:FLOWPI_PORT = "5000" }
if (-not $env:FLOWPI_FRONTEND_PORT) { $env:FLOWPI_FRONTEND_PORT = "8000" }
if (-not $env:FLOWPI_ENABLE_GPIO) { $env:FLOWPI_ENABLE_GPIO = "false" }
$env:PYTHONPATH = $baseDir

Write-Host "Starting backend..."
$backend = Start-Process -FilePath $pythonExe -ArgumentList "-m", "backend.app" -WorkingDirectory $baseDir -PassThru

Write-Host "Starting frontend..."
$frontendDir = Join-Path $baseDir "frontend"
$frontend = Start-Process -FilePath $pythonExe -ArgumentList "-m", "http.server", $env:FLOWPI_FRONTEND_PORT -WorkingDirectory $frontendDir -PassThru

Write-Host "-----------------------------------"
Write-Host "Backend PID: $($backend.Id)"
Write-Host "Frontend PID: $($frontend.Id)"
Write-Host "System running!"
Write-Host "Open: http://localhost:$($env:FLOWPI_FRONTEND_PORT)"
Write-Host "-----------------------------------"

try {
    Wait-Process -Id $backend.Id, $frontend.Id
}
finally {
    Write-Host "Stopping..."
    foreach ($proc in @($backend, $frontend)) {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force
        }
    }
}
