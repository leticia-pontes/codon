#!/bin/bash
# Script de instalação automática do Codon para Linux/macOS
# Executa: ./install.sh

set -e  # Para em caso de erro

echo "========================================"
echo " Instalador Codon - Compilador LLVM"
echo "========================================"
echo

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "[ERRO] Python 3 não encontrado! Instale Python 3.10+ primeiro."
    exit 1
fi

echo "[1/4] Verificando ambiente virtual..."
if [ ! -d ".venv" ]; then
    echo "Criando novo ambiente virtual..."
    python3 -m venv .venv
else
    echo "Ambiente virtual já existe, usando o existente."
fi

echo "[2/4] Ativando ambiente virtual..."
source .venv/bin/activate

echo "[3/4] Instalando dependências..."
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[4/4] Instalando Codon globalmente..."
pip install -e .

echo
echo "========================================"
echo " Instalação concluída com sucesso!"
echo "========================================"
echo
echo "Para usar o Codon de qualquer lugar:"
echo "  1. Ative o ambiente virtual:"
echo "     source .venv/bin/activate"
echo
echo "  2. Execute seus programas:"
echo "     codon run examples/basicos/hello_world.cd"
echo "     codon build meu_programa.cd"
echo
echo "Nota: Você precisa ativar o venv apenas uma vez por sessão do terminal."
echo

# Torna o script executável para próximas vezes
chmod +x install.sh
