import unittest
from src.lexer.analisador_lexico_completo import Lexer, ErrorHandler, LexicalError

class TestLexerErroLexico(unittest.TestCase):
    """Testa se o lexer registra erro ao encontrar caracteres inválidos."""

    def test_lexer_records_invalid_char_error(self):
        src = 'function x = 10\n$'  # $ é inválido
        error_handler = ErrorHandler()
        lx = Lexer(src, error_handler=error_handler)

        # percorre todos os tokens
        while True:
            t = lx.next()
            if t is None:
                break

        # verifica se algum LexicalError foi registrado
        self.assertTrue(error_handler.has_errors(), "Lexer não registrou erro")
        types = [type(e).__name__ for e in error_handler.errors]
        self.assertIn("LexicalError", types, "Deveria conter LexicalError")


if __name__ == "__main__":
    unittest.main()
