param(
    [string]$ExePath = (Join-Path $PSScriptRoot "..\dist\KindleManager.exe")
)

$resolvedExe = (Resolve-Path $ExePath -ErrorAction Stop).Path
$existingIds = @(
    Get-Process KindleManager -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $resolvedExe } |
        Select-Object -ExpandProperty Id
)

Start-Process -FilePath $resolvedExe | Out-Null
Start-Sleep -Seconds 8

$started = @(
    Get-Process KindleManager -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $resolvedExe -and $_.Id -notin $existingIds }
)

try {
    if ($started.MainWindowTitle -contains "Unhandled exception in script") {
        throw "Packaged application opened an unhandled-exception dialog."
    }
    if ($started.MainWindowTitle -notcontains "Kindle Manager") {
        throw "Kindle Manager main window did not appear."
    }
    Write-Output "PASS: Kindle Manager main window opened successfully."
}
finally {
    $started | Stop-Process -Force -ErrorAction SilentlyContinue
}
