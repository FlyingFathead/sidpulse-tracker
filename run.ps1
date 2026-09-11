$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$sidpulsePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$sidpulseRuntimeCheck = @'
import struct, sys
ready = sys.version_info >= (3, 10) and struct.calcsize("P") == 8
if ready:
    print(sys.executable)
sys.exit(0 if ready else 1)
'@
$sidpulseDependencyCheck = @'
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys
try:
    requirements = [line.split("#", 1)[0].strip() for line in Path("requirements.txt").read_text().splitlines()]
    pins = [line.split("==", 1) for line in requirements if line]
    ready = all(len(pin) == 2 and version(pin[0]) == pin[1] for pin in pins)
except (PackageNotFoundError, OSError):
    ready = False
sys.exit(0 if ready else 1)
'@

function Test-SidpulseRuntime($Executable, $PrefixArgs = @()) {
    try {
        $result = @($sidpulseRuntimeCheck | & $Executable @PrefixArgs - 2>$null)
        if ($LASTEXITCODE -eq 0 -and $result.Count -gt 0) { return $result[-1] }
    } catch { }
    return $null
}

function Find-SidpulseRuntime {
    $launcher = Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($launcher) {
        # Listing installed interpreters does not request a Python download.
        try { $installed = @(& $launcher.Source -0p 2>$null) } catch { $installed = @() }
        foreach ($entry in $installed) {
            if ($entry -match '(?<path>(?:[A-Za-z]:\\|\\\\).+?python\.exe)\s*$') {
                $found = Test-SidpulseRuntime $Matches['path']
                if ($found) { return $found }
            }
        }
    }
    # Also find a just-installed interpreter before a new terminal refreshes PATH.
    $locations = @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
    $command = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notmatch '\\WindowsApps\\') { $locations += $command.Source }
    foreach ($location in $locations) {
        if (Test-Path -LiteralPath $location) {
            $found = Test-SidpulseRuntime $location
            if ($found) { return $found }
        }
    }
    return $null
}

$sidpulseEnvironmentReady = $false
if (Test-Path -LiteralPath $sidpulsePython) {
    $sidpulseEnvironmentReady = [bool](Test-SidpulseRuntime $sidpulsePython)
}
$sidpulsePackagesReady = $false
if ($sidpulseEnvironmentReady) {
    $sidpulseDependencyCheck | & $sidpulsePython -
    $sidpulsePackagesReady = $LASTEXITCODE -eq 0
}
if (-not $sidpulseEnvironmentReady -or -not $sidpulsePackagesReady) {
    $sidpulseBasePython = if ($sidpulseEnvironmentReady) { $sidpulsePython } else { Find-SidpulseRuntime }
    Write-Host ''
    Write-Host 'SIDpulse Tracker needs these to run:'
    Write-Host ('  Python 3.10 or newer (64-bit): ' + $(if ($sidpulseBasePython) { 'found' } else { 'missing' }))
    Write-Host ''
    Write-Host 'The following Python dependencies are required and need to be downloaded:'
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'requirements.txt') | ForEach-Object { Write-Host $_ }
    Write-Host ''
    Write-Host 'Setup will install missing packages into this folder''s .venv environment.'
    if (-not $sidpulseBasePython) {
        Write-Host 'Python 3.12 will also be installed for your Windows account using WinGet.'
    }
    Write-Host 'An internet connection is needed for downloads.'
    do {
        if ([Console]::IsInputRedirected) {
            Write-Host 'Continue? [Y/n] ' -NoNewline
            $answer = [Console]::ReadLine()
        } else {
            $answer = Read-Host 'Continue? [Y/n]'
        }
        if ($null -eq $answer) { Write-Host 'Setup cancelled.'; exit 0 }
        $answer = $answer.Trim()
    } while ($answer -notmatch '^(?i:y|yes|n|no)?$')
    if ($answer -match '^(?i:n|no)$') { Write-Host 'Setup cancelled. Nothing was installed.'; exit 0 }

    if (-not $sidpulseBasePython) {
        $winget = Get-Command winget.exe -CommandType Application -ErrorAction SilentlyContinue
        if (-not $winget) {
            Write-Host 'WinGet is unavailable. Install 64-bit Python from https://www.python.org/downloads/windows/'
            Write-Host 'Then run run.cmd again.'
            exit 1
        }
        & $winget.Source install --id Python.Python.3.12 --exact --source winget --scope user --architecture x64 --silent --accept-source-agreements --accept-package-agreements --disable-interactivity
        if ($LASTEXITCODE -ne 0) { throw 'Python installation did not finish. Install Python from python.org, then run run.cmd again.' }
        $sidpulseBasePython = Find-SidpulseRuntime
        if (-not $sidpulseBasePython) { throw 'Python was installed but could not be found. Open a new terminal and run run.cmd again.' }
    }
    if (-not $sidpulseEnvironmentReady) {
        if (Test-Path -LiteralPath '.venv') {
            $sidpulseBackup = '.venv-before-setup-' + [guid]::NewGuid().ToString('N')
            Move-Item -LiteralPath '.venv' -Destination $sidpulseBackup
            Write-Host "Previous environment kept in $sidpulseBackup"
        }
        & $sidpulseBasePython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python virtual environment.' }
    }
    & $sidpulsePython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'SIDpulse dependency installation failed. Check the error above and run run.cmd again.' }
}
& $sidpulsePython -m sidpulse @args
$sidpulseExitCode = $LASTEXITCODE
if ($sidpulseExitCode -ne 0) {
    Write-Host ('SIDpulse Tracker exited with error code ' + $sidpulseExitCode)
    $sidpulseLogRoot = if ($env:SIDPULSE_CONFIG_HOME) { Join-Path $env:SIDPULSE_CONFIG_HOME 'logs' } else { Join-Path $env:LOCALAPPDATA 'SIDpulse\logs' }
    Write-Host ('Crash reports: ' + $sidpulseLogRoot)
    if (-not [Console]::IsInputRedirected -and $args -notcontains '--headless-smoke') {
        Read-Host 'Press Enter to close'
    }
}
exit $sidpulseExitCode
