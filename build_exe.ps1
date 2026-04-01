param(
    [string]$AppName = "MuhasebeBelgeCikarim"
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py -3"
    }
    throw "Python bulunamadi. Lutfen Python 3.10+ kur ve tekrar dene."
}

$pythonCmd = Resolve-Python

Write-Host "Python komutu: $pythonCmd"
Write-Host "Build bagimliliklari yukleniyor..."
Invoke-Expression "$pythonCmd -m pip install -r requirements.txt"
Invoke-Expression "$pythonCmd -m pip install -r requirements-build.txt"

if (Test-Path -LiteralPath ".\build") {
    Remove-Item -LiteralPath ".\build" -Recurse -Force
}
if (Test-Path -LiteralPath ".\dist") {
    Remove-Item -LiteralPath ".\dist" -Recurse -Force
}
if (Test-Path -LiteralPath ".\$AppName.spec") {
    Remove-Item -LiteralPath ".\$AppName.spec" -Force
}

Write-Host "EXE olusturuluyor..."
Invoke-Expression "$pythonCmd -m PyInstaller --noconfirm --clean --windowed --onefile --name $AppName app.py"

Write-Host ""
Write-Host "Tamamlandi."
Write-Host "Cikti: .\dist\$AppName.exe"
