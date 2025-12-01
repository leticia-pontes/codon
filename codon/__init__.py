#!/usr/bin/env python3
"""
Codon Compiler - Entry point para instalação via pip.
Permite executar 'codon run <arquivo>' de qualquer lugar.
"""

import sys
import os

def main():
    """Entry point para o comando 'codon' instalado globalmente."""
    # Importa a função de compilação
    from src.compilador import compile_cd
    
    def print_help():
        print("Uso:")
        print("  codon run <arquivo.cd>     # Compila e executa")
        print("  codon build <arquivo.cd>   # Apenas compila (imprime LLVM IR)")
        print("  codon build <arquivo.cd> --quiet  # Sem mensagens informativas")
    
    if len(sys.argv) < 3:
        print_help()
        sys.exit(1)
    
    cmd = sys.argv[1]
    arquivo = sys.argv[2]
    quiet = '--quiet' in sys.argv or '-q' in sys.argv
    
    # Converte para caminho absoluto para funcionar de qualquer diretório
    if not os.path.isabs(arquivo):
        arquivo = os.path.abspath(arquivo)
    
    if not arquivo.endswith(".cd"):
        print("[ERRO] Arquivo deve ter extensão .cd")
        sys.exit(1)
    
    if not os.path.exists(arquivo):
        print(f"[ERRO] Arquivo não encontrado: {arquivo}")
        sys.exit(1)
    
    if cmd == "run":
        if not quiet:
            print(f"[INFO] Compilando e executando: {os.path.basename(arquivo)}")
            print(f"[INFO] Caminho: {arquivo}")
            print("")
        
        compile_cd(arquivo, run=True)
    elif cmd == "build":
        # Mensagem informativa
        if not quiet:
            print(f"[INFO] Compilando: {os.path.basename(arquivo)}")
            print(f"[INFO] Caminho: {arquivo}")
            print("[INFO] Gerando LLVM IR...")
        
        ir = compile_cd(arquivo, run=False)
        
        # Verifica se compilou com sucesso
        if isinstance(ir, str):
            if quiet:
                # Modo quiet: imprime apenas o LLVM IR (para redirecionar)
                print(ir)
            else:
                # Modo normal: apenas confirma sucesso
                print("[OK] Compilação concluída com sucesso!")
                print(f"[INFO] LLVM IR gerado ({len(ir)} caracteres)")
                print("[DICA] Para ver/salvar o IR: codon build {0} --quiet > output.ll".format(os.path.basename(arquivo)))
        else:
            print("[ERRO] Falha na compilação", file=sys.stderr)
            sys.exit(1)
    else:
        print_help()

if __name__ == '__main__':
    main()
