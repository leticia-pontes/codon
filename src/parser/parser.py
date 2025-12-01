from .ast.ast_base import Parser, TokenStream, ASTNode
from src.lexer.analisador_lexico_completo import Lexer
import os

def parse_cd(arquivo: str) -> ASTNode:
    """
    Lê um arquivo .cd, tokeniza usando Lexer e retorna a AST Programa.
    """
    arquivo_path = arquivo if os.path.isabs(arquivo) else os.path.abspath(arquivo)

    with open(arquivo_path, "r", encoding="utf-8") as f:
        codigo = f.read()

    lexer = Lexer(codigo)
    ts = TokenStream(lexer)
    parser = Parser(ts)
    return parser.parse()
