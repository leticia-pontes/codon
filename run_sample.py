from src.lexer.analisador_lexico_completo import Lexer
from src.utils.erros import ErrorHandler

file_path = "examples/basicos/sample_error.cd"

with open(file_path, "r", encoding="utf-8") as f:
    source_code = f.read()

# Inicializa o ErrorHandler e o Lexer
error_handler = ErrorHandler()
lexer = Lexer(source_code, error_handler=error_handler)

# Gera os tokens
tokens = lexer.tokenize_all()

# Mostra os tokens
if tokens:
    print("Tokens gerados com sucesso:")
    for t in tokens:
        print(t)

# Mostra os erros, se houver
if error_handler.has_errors():
    print("\nErros encontrados:")
    for err in error_handler.errors:
        # err.__class__.__name__ dá o tipo do erro
        print(f"[{err.__class__.__name__}] {err}")
