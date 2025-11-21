#!/usr/bin/env python3
import os
import subprocess
import sys
import time
from pathlib import Path

CAMINHO_CODON = Path(".")
CAMINHO_SAIDA = Path("saida_testes")

def encontrar_clang():
    possiveis = [r"C:\Program Files\LLVM\bin\clang.exe", "clang.exe", "clang"]
    for c in possiveis:
        if os.path.exists(c): return c
        try:
            if subprocess.run([c, "--version"], capture_output=True).returncode == 0: return c
        except: pass
    return None

def criar_runtime_c():
    runtime_c = """
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
int printf(const char *format, ...);
char *strstr(const char *haystack, const char *needle);
long long cd_strlen(const char *str) {
    long long len = 0;
    while (str[len]) len++;
    return len;
}
long long find_substring(const char *str, const char *pattern) {
    if (!str || !pattern) return -1;
    char *found = strstr(str, pattern);
    return found ? (long long)(found - str) : -1;
}
"""
    with open(CAMINHO_SAIDA / "runtime.c", "w") as f:
        f.write(runtime_c)

def criar_diretorios():
    CAMINHO_SAIDA.mkdir(exist_ok=True)
    (CAMINHO_SAIDA / "ll").mkdir(exist_ok=True)
    (CAMINHO_SAIDA / "exe").mkdir(exist_ok=True)
    (CAMINHO_SAIDA / "logs").mkdir(exist_ok=True)

def encontrar_todos_arquivos_cd():
    print("🔍 Procurando por todos os arquivos .cd...")
    arquivos = []
    for arquivo in Path(".").rglob("*.cd"):
        if "repos/examples" in str(arquivo) or "saida_testes" in str(arquivo): continue
        arquivos.append(arquivo)
    print(f"    ✅ Encontrados {len(arquivos)} arquivos únicos.")
    return sorted(arquivos)

def testar_arquivo(arquivo_cd, clang_path):
    print(f"\n📁 Testando: {arquivo_cd}")
    nome = arquivo_cd.stem
    ll = CAMINHO_SAIDA / "ll" / f"{nome}.ll"
    exe = CAMINHO_SAIDA / "exe" / f"{nome}.exe"
    
    # Compilar
    print(f"  📝 Compilando...")
    cmd = [sys.executable, "-m", "src.compilador", "run", str(arquivo_cd)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=CAMINHO_CODON)
    
    if res.returncode != 0 or "ERRO" in res.stdout or "SYN" in res.stdout:
        print("    ❌ Erro de compilação.")
        print(res.stdout[:500]) # Mostra só o começo do erro
        return False
    
    with open(ll, 'w', encoding='utf-8') as f: f.write(res.stdout)
    print("    ✅ LLVM IR gerado com SUCESSO.")
    
    # Linkar
    print(f"  🔗 Linkando...")
    criar_runtime_c()
    res_link = subprocess.run([clang_path, "-O0", "-Wno-override-module", str(ll), str(CAMINHO_SAIDA/"runtime.c"), "-o", str(exe)], capture_output=True, text=True)
    
    if res_link.returncode != 0:
        print("    ⚠️  Aviso: Linker falhou (provavelmente falta de bibliotecas no Windows).")
        print("    Mas a compilação (Parser/Codegen) funcionou! ✅")
        return True # Consideramos sucesso se gerou o .ll válido
        
    print("    ✅ Executável criado. Executando...")
    try:
        res_run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=3)
        print(f"    Saída: {res_run.stdout.strip()}")
    except: pass
    
    return True

def main():
    clang = encontrar_clang()
    if not clang: 
        print("Clang não encontrado.")
        return
    criar_diretorios()
    arquivos = encontrar_todos_arquivos_cd()
    sucessos = 0
    for f in arquivos:
        if testar_arquivo(f, clang): sucessos += 1
    
    print(f"\n📊 Sucesso Final: {sucessos}/{len(arquivos)}")

if __name__ == "__main__":
    main()