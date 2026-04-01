$ErrorActionPreference = "Stop"

function Resolve-Python {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return @{ Exe = $venvPython; Args = @() }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Exe = "python"; Args = @() }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Exe = "py"; Args = @("-3") }
    }
    throw "Python bulunamadi. Python 3.10+ kurup tekrar dene."
}

$python = Resolve-Python
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
$appPath = Join-Path $PSScriptRoot "app.py"

# Eksik bagimlilik varsa otomatik kur.
& $python.Exe @($python.Args + @("-c", "import pypdf")) 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Eksik paketler bulundu. requirements.txt kuruluyor..."
    & $python.Exe @($python.Args + @("-m", "pip", "install", "-r", $requirementsPath))
    if ($LASTEXITCODE -ne 0) {
        throw "Bagimlilik kurulumu basarisiz oldu."
    }
}

& $python.Exe @($python.Args + @($appPath))
