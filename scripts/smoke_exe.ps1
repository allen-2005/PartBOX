param([Parameter(Mandatory=$true)][string]$Executable)
$ErrorActionPreference = "Stop"
$TestData = Join-Path $env:TEMP ("PartBOX-smoke-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TestData | Out-Null
$env:PARTBOX_DATA_DIR = $TestData
$Process = Start-Process -FilePath $Executable -PassThru -WindowStyle Hidden
$DatabasePath = Join-Path $TestData "partbox.db"

function Get-DescendantProcessIds([int]$ParentId) {
    $Result = @()
    foreach ($Child in Get-CimInstance Win32_Process -Filter "ParentProcessId=$ParentId") {
        $Result += [int]$Child.ProcessId
        $Result += Get-DescendantProcessIds -ParentId ([int]$Child.ProcessId)
    }
    return $Result
}

try {
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    while (-not (Test-Path -LiteralPath $DatabasePath) -and [DateTime]::UtcNow -lt $Deadline) {
        $Process.Refresh()
        if ($Process.HasExited) {
            throw "PartBOX exited during startup with code $($Process.ExitCode)"
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-Path -LiteralPath $DatabasePath)) {
        throw "PartBOX did not initialize an empty database within 60 seconds"
    }
    Write-Host "Packaged executable startup smoke passed."
}
finally {
    $ProcessIds = @(Get-DescendantProcessIds -ParentId $Process.Id) + @($Process.Id)
    foreach ($ProcessId in ($ProcessIds | Select-Object -Unique | Sort-Object -Descending)) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
    $ResolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $ResolvedTestData = [IO.Path]::GetFullPath($TestData)
    if ($ResolvedTestData.StartsWith($ResolvedTemp, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $ResolvedTestData -Recurse -Force -ErrorAction SilentlyContinue
    }
}
