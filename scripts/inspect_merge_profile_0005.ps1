# Owner approval required: one fixed-profile read-only inspection, no retry.
$ErrorActionPreference = 'Stop'
$inspectionBackend = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\backend'))
$inspectionPython = Join-Path $inspectionBackend '.venv\Scripts\python.exe'
Push-Location -LiteralPath $inspectionBackend
try {
    & $inspectionPython -B -W error::getpass.GetPassWarning -m release_support.profile_inspection --confirm-profile-test
    $inspectionCaptureExit = $LASTEXITCODE
    if ($inspectionCaptureExit -ne 0) { throw 'Inspection capture incomplete; preserve evidence and stop' }
}
finally {
    Pop-Location
}
