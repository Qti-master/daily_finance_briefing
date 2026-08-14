[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$PythonPath = "",
    [string]$OutputDir = "reports",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BriefingArgs = @()
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$BriefingScript = Join-Path $PSScriptRoot "daily_finance_briefing.py"

function Resolve-Python {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        $PathToUse = $RequestedPath
        if (-not [System.IO.Path]::IsPathRooted($PathToUse)) {
            $PathToUse = Join-Path $Root $PathToUse
        }
        if (Test-Path -LiteralPath $PathToUse) {
            return (Resolve-Path -LiteralPath $PathToUse).Path
        }
        throw "Requested PythonPath was not found: $RequestedPath"
    }

    $LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $LocalPython) {
        return (Resolve-Path -LiteralPath $LocalPython).Path
    }

    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) {
        return $PythonCommand.Source
    }

    $PyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($PyCommand) {
        $InstalledPythons = & $PyCommand.Source -0p 2>&1 | Out-String
        if ($InstalledPythons -and ($InstalledPythons -notmatch "No installed Pythons found")) {
            return $PyCommand.Source
        }
    }

    throw "Python was not found. Install Python 3.9+ and run: python -m pip install -r requirements.txt"
}

$Python = Resolve-Python -RequestedPath $PythonPath

Push-Location $Root
try {
    & $Python $BriefingScript --output-dir $OutputDir @BriefingArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
