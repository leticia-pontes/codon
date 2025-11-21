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

# unittest é builtin, mas se houver libs extras, instale:
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
}

Write-Host "==> Rodando todos os testes com unittest..."
python -m unittest discover -s test -p "*.py" -v

Write-Host "==> Testes finalizados."
