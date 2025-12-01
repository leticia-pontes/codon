@echo off
REM Script de instalação automática do Codon para Windows
REM Executa: install.bat

echo ========================================
echo  Instalador Codon - Compilador LLVM
echo ========================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado! Instale Python 3.10+ primeiro.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Verificando ambiente virtual...
if not exist ".venv" (
    echo Criando novo ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual
        pause
        exit /b 1
    )
) else (
    echo Ambiente virtual ja existe, usando o existente.
)

echo [2/4] Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo [3/4] Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias
    pause
    exit /b 1
)

echo [4/4] Instalando Codon globalmente...
pip install -e .
if errorlevel 1 (
    echo [ERRO] Falha ao instalar Codon
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Instalacao concluida com sucesso!
echo ========================================
echo.
echo Para usar o Codon de qualquer lugar:
echo   1. Ative o ambiente virtual:
echo      .venv\Scripts\activate
echo.
echo   2. Execute seus programas:
echo      codon run examples\basicos\hello_world.cd
echo      codon build meu_programa.cd
echo.
echo Nota: Voce precisa ativar o venv apenas uma vez por sessao do terminal.
echo.
pause
