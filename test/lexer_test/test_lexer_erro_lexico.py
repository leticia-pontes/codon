import unittest
from src.lexer.analisador_lexico_completo import Lexer, LexicalError

class TestLexerErroLexico(unittest.TestCase):
    """Testa se o lexer lança exceção ao encontrar caracteres inválidos."""

    def test_lexer_raises_on_invalid_char(self):
        # caractere inválido (por exemplo, símbolo não reconhecido)
        src = 'function x = 10\n$'  # $ é inválido
        lx = Lexer(src)

        with self.assertRaises(LexicalError):
            while True:
                t = lx.next()
                if t is None:
                    break


if __name__ == "__main__":
    unittest.main()
