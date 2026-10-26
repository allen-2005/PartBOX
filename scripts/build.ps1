$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:QT_QPA_PLATFORM = "offscreen"
& "$ProjectRoot\.venv\Scripts\python.exe" -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Automated tests failed; packaging stopped." }
& "$ProjectRoot\.venv\Scripts\pyinstaller.exe" --noconfirm --clean "$ProjectRoot\PartBOX.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
Copy-Item -LiteralPath "$ProjectRoot\src\partbox\ui\forms\main_window.ui" -Destination "$ProjectRoot\dist\main_window.ui" -Force
Copy-Item -LiteralPath "$ProjectRoot\dist\PartBOX.exe" -Destination "$ProjectRoot\PartBOX.exe" -Force
New-Item -ItemType Directory -Path "$ProjectRoot\dist\logo" -Force | Out-Null
Copy-Item -LiteralPath "$ProjectRoot\assets\partbox-wordmark-v1.png" -Destination "$ProjectRoot\dist\logo\partbox-wordmark-v1.png" -Force
Copy-Item -LiteralPath "$ProjectRoot\assets\partbox-chinese-wordmark-v1.png" -Destination "$ProjectRoot\dist\logo\partbox-chinese-wordmark-v1.png" -Force
Write-Host "Built: $ProjectRoot\dist\PartBOX.exe"
Write-Host "Desktop project launcher updated: $ProjectRoot\PartBOX.exe"
Write-Host "Editable UI: $ProjectRoot\dist\main_window.ui"
Write-Host "Logo assets: $ProjectRoot\dist\logo"
