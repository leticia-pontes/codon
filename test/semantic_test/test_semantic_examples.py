import unittest
import os
import glob
from src.utils.erros import ErrorHandler, SemanticError

# --- IMPORTAÇÕES NECESSÁRIAS ---
from src.lexer.analisador_lexico_completo import TokenStream, Lexer
from src.parser.parser import Parser
from src.semantic.analyzer import SemanticAnalyzer

# Define a extensão dos seus arquivos de código.
FILE_EXTENSION = "*.cd"

# Define o diretório raiz dos seus exemplos
# A pasta 'examples' deve estar no mesmo nível do projeto que 'src' e 'test'
ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')

# ======================================================================
# Lógica Auxiliar para Processamento de Arquivos
# ======================================================================

def process_file_and_check_errors(filepath, expected_errors, self):
    """
    Função principal que executa a pipeline completa (Lexer, Parser, Semântica)
    e faz a asserção final.
    """
    # Log informativo
    print(f"        [INFO] Testando {filepath} ...")
    
    with open(filepath, 'r', encoding='utf8') as f:
        code = f.read()

    # 1. Análise Lexical
    lexer_eh = ErrorHandler() # Use um handler para erros lexicais também
    try:
        lexer = Lexer(code, error_handler=lexer_eh)

        # CORREÇÃO CRÍTICA: O TokenStream recebe a instância do Lexer, não uma lista de tokens.
        token_stream = TokenStream(lexer)

    except Exception as e:
        self.fail(f"Erro inesperado no Lexer em {filepath}: {e}")
        return

    if lexer_eh.has_errors():
        # Imprime os erros lexicais para visualização
        for err in lexer_eh.errors:
            print(f"{err}")
        self.fail(f"Erros Lexicais (não-fatais) em {filepath}: {lexer_eh.errors}")
        return


    # 2. Análise Sintática
    parser_eh = ErrorHandler()
    parser = Parser(token_stream, error_handler=parser_eh)

    try:
        ast_root = parser.parse()
    except Exception as e:
        # Erro fatal no parser
        self.fail(f"Erro Sintático FATAL em {filepath}: {e}")
        return

    if parser_eh.has_errors():
        # Erros não-fatais (recuperáveis) no parser
        self.fail(f"Erros Sintáticos (não-fatais) em {filepath}: {parser_eh.errors}")
        return

    # 3. Análise Semântica
    semantic_eh = ErrorHandler()
    analyzer = SemanticAnalyzer(error_handler=semantic_eh)

    try:
        analyzer.analyze(ast_root)
    except Exception as e:
        # Erros internos do analisador (ex: Attribute Error)
        self.fail(f"Erro INTERNO no Analisador Semântico em {filepath}: {e}")
        return

    # 4. Asserção
    # Verifica se o número de erros encontrados corresponde ao esperado
    self.assertEqual(
        len(semantic_eh.errors),
        expected_errors,
        f"Esperado {expected_errors} erros semânticos em '{filepath}', mas encontrado {len(semantic_eh.errors)}.\nErros: {semantic_eh.errors}"
    )


def create_example_test(filepath, expected_errors=0):
    """Gera dinamicamente uma função de teste."""

    def test_example_file(self):
        process_file_and_check_errors(filepath, expected_errors, self)

    # Cria um nome de função único e legível para o unittest
    relative_path = os.path.relpath(filepath, start=ROOT_DIR)
    # Limpa o nome para ser um identificador Python válido
    test_name = 'test_semantic_example_' + relative_path.replace(os.path.sep, '__').replace('.', '_')
    test_example_file.__name__ = test_name
    return test_example_file

# ======================================================================
# Geração Dinâmica de Testes
# ======================================================================

class TestSemanticExamples(unittest.TestCase):
    pass

# Procura todos os arquivos de código nos subdiretórios de 'examples'
file_paths = glob.glob(os.path.join(ROOT_DIR, '**', FILE_EXTENSION), recursive=True)

# Organiza os arquivos por diretório para logs mais claros
files_by_dir = {}
for filepath in file_paths:
    dir_name = os.path.dirname(filepath)
    if dir_name not in files_by_dir:
        files_by_dir[dir_name] = []
    files_by_dir[dir_name].append(filepath)

# Imprime a estrutura de testes que será executada
print("\n" + "="*80)
print("TESTES SEMANTICOS - ESTRUTURA DE ARQUIVOS")
print("="*80)
for dir_name in sorted(files_by_dir.keys()):
    print(f"\n[INFO] Entrando em: {dir_name}\n")
    for filepath in sorted(files_by_dir[dir_name]):
        filename = os.path.basename(filepath)
        print(f"   - {filename}")
print("\n" + "="*80 + "\n")

# Gera os testes dinamicamente
for filepath in file_paths:
    # 1. Determina o número de erros esperado (Convenção)

    # Convenção: Assume 1 erro para arquivos em pastas "invalidos" ou com "error" no nome
    is_invalid_example = "invalidos" in filepath.lower() or "error" in os.path.basename(filepath).lower()

    if is_invalid_example:
        # ATENÇÃO: Ajuste a contagem de erros se um arquivo inválido tiver mais de um erro
        expected_errors = 1
    else:
        # Assume 0 erros para exemplos válidos
        expected_errors = 0

    # 2. Gera e anexa a função de teste
    test_func = create_example_test(filepath, expected_errors)
    setattr(TestSemanticExamples, test_func.__name__, test_func)

if __name__ == '__main__':
    unittest.main()