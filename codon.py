#!/usr/bin/env python3

import sys
from src.compilador import compile_cd

def print_help():
    print("Uso:")
    print("  codon run <arquivo.cd>    # Compila e executa")
    print("  codon build <arquivo.cd>  # Apenas compila")

if len(sys.argv) < 3:
    print_help()
    sys.exit(1)

cmd = sys.argv[1]
arquivo = sys.argv[2]

if not arquivo.endswith(".cd"):
    print("[ERRO] Arquivo deve ter extensão .cd")
    sys.exit(1)

if cmd == "run":
    compile_cd(arquivo, run=True)
elif cmd == "build":
    ir = compile_cd(arquivo, run=False)
    # Imprime o LLVM IR resultante
    if isinstance(ir, str):
        print(ir)
else:
    print_help()
