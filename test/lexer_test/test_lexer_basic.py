import unittest
from src.lexer.analisador_lexico_completo import Lexer


class TestLexerSimple(unittest.TestCase):
    def test_tokens_simple(self):
        src = 'var x = 42;\nif (x > 0) x = x - 1;'
        lexer = Lexer(src)
        toks = lexer.tokenize_all()
        kinds = [t.tipo for t in toks]

        # verifica presença de tokens chave
        self.assertIn('KWD', kinds)     # var -> KWD
        self.assertIn('ID', kinds)
        self.assertIn('DEC_INT', kinds)
        self.assertIn('SEMI', kinds)


if __name__ == "__main__":
    unittest.main()
