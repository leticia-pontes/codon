Param()
$root = Join-Path $PSScriptRoot ".."
Set-Location $root

Write-Host "==> Criando/ativando virtualenv (.venv) ..."
python -m venv .venv

if (Test-Path ".venv/Scripts/Activate.ps1") {
    Write-Host "==> Ativando .venv (Windows PS)..."
    & ".\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "==> Ativando .venv (fallback)..."
    . .\.venv\Scripts\Activate
}

Write-Host "==> Instalando dependências..."
pip install --upgrade pip
pip install pytest

Write-Host "==> Rodando pytest..."
pytest -q

Write-Host "==> Testes finalizados."
