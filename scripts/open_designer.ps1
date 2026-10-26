param(
    [string]$UiFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Designer = Join-Path $ProjectRoot ".venv\Scripts\pyside6-designer.exe"
if (-not $UiFile) {
    $UiFile = Join-Path $ProjectRoot "src\partbox\ui\forms\main_window.ui"
}
if (-not (Test-Path -LiteralPath $Designer)) { throw "Qt Designer 不存在：$Designer" }
if (-not (Test-Path -LiteralPath $UiFile)) { throw "UI 文件不存在：$UiFile" }
Start-Process -FilePath $Designer -ArgumentList @($UiFile)
