import sys
import os

# Garante que o Python encontre os módulos a partir da raiz
sys.path.append(os.getcwd())

from src.lexer import Lexer, TokenStream
from src.parser.descendente.parser_ll1 import Parser
from src.semantic.analyzer import SemanticAnalyzer
from src.utils.erros import ErrorHandler

# Tenta importar o gerador, se existir
try:
    from src.codegen.gerador_codigo import CodeGenerator
    TEM_GERADOR = True
except ImportError:
    TEM_GERADOR = False

def adapt_tokens(tokens):
    """
    Ajusta tokens para compatibilidade.
    Remove 'dna', 'prot', 'rna' das palavras-chave para que o Parser
    possa tratá-los como tipos personalizados ou identificadores.
    """
    keywords = {
        'program', 'var', 'const', 'void', 'function', 'def', 'let', 'class',
        'if', 'else', 'while', 'return', 'print',
        'true', 'false', 'new', 'int', 'bool', 'float', 'string', 'char', 'any'
        # 'dna', 'prot', 'rna' removidos intencionalmente
    }
    
    for t in tokens:
        # Se o token foi marcado como ID mas está na lista de keywords, vira KWD
        if t.tipo == 'ID' and t.valor in keywords:
            t.tipo = 'KWD'
        
        # Garante atributos para o Parser
        if not hasattr(t, 'kind'): t.kind = t.tipo
        if not hasattr(t, 'lexeme'): t.lexeme = t.valor
        if not hasattr(t, 'line'): t.line = t.linha
        if not hasattr(t, 'col'): t.col = t.coluna
        if not hasattr(t, 'literal'): t.literal = None
    return tokens

def ler_arquivo(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filename, 'r', encoding='latin-1') as f:
            return f.read()

def main():
    if len(sys.argv) < 3:
        print("Uso: python -m src.compilador run <arquivo.cd>")
        return

    filename = sys.argv[2]
    if not os.path.exists(filename):
        print(f"Erro: Arquivo nao encontrado: {filename}")
        return

    source = ler_arquivo(filename)
    print(f"Compilando {filename}...", file=sys.stderr)

    err = ErrorHandler()
    
    # 1. Lexer
    lex = Lexer(source, err)
    tokens = adapt_tokens(lex.tokenize_all())
    if err.has_errors(): return

    # 2. Parser
    parser = Parser(TokenStream(tokens), err)
    ast = parser.parse()
    if err.has_errors(): return

    # 3. Semantic Analyzer
    analyzer = SemanticAnalyzer(err)
    try:
        analyzer.analyze(ast)
    except Exception as e:
        print(f"[ERRO Semantico Critico] {e}")
        return
    if err.has_errors(): return

    # 4. Code Generation
    if TEM_GERADOR:
        print("Gerando codigo LLVM IR...")
        try:
            gen = CodeGenerator()
            ir_code = str(gen.generate(ast))
            out_file = filename.replace(".cd", ".ll")
            with open(out_file, "w", encoding='utf-8') as f:
                f.write(ir_code)
            print(f"[SUCESSO] Codigo intermediario gerado em: {out_file}")
        except Exception as e:
            print(f"[ERRO] Falha na geracao de codigo: {e}")
    else:
        print("[AVISO] Compilacao finalizada sem geracao de codigo (modulo ausente).")

if __name__ == "__main__":
    main()