import unittest
from src.lexer.analisador_lexico_completo import Lexer, TokenStream

SAMPLE = r'''
// comentário simples
function soma(a, b) {
  return a + b;
}

dna"ACGT" prot"MK" "uma string" 123 4.56 7.8e-2 ...
'''

class TestLexerTokenizacao(unittest.TestCase):
    """Testa se o lexer reconhece corretamente os tokens básicos."""

    def test_tokenize_basic_sequence(self):
        lx = Lexer(SAMPLE)
        ts = TokenStream(lx)
        tipos = []

        while True:
            t = ts.next()
            if t is None:
                break
            # dependendo da implementação, o atributo pode ser kind (não tipo)
            tipos.append(getattr(t, "kind", getattr(t, "tipo", None)))

        # verifica que os principais tipos de token aparecem na sequência
        self.assertTrue("KWD" in tipos or "ID" in tipos)
        self.assertIn("DNA_LIT", tipos)
        self.assertIn("PROT_LIT", tipos)
        self.assertIn("STRING", tipos)
        self.assertIn("DEC_INT", tipos)   # 123
        self.assertIn("FLOAT", tipos)     # 4.56
        self.assertIn("FLOAT_EXP", tipos) # 7.8e-2
        self.assertIn("DOT3", tipos)      # ...


if __name__ == "__main__":
    unittest.main()
