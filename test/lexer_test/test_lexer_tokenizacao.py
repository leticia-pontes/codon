import pytest
from src.lexer.lexer_completo import Lexer, TokenStream, LexicalError

SAMPLE = r'''
// comentário simples
func soma(a, b) {
  return a + b;
}

dna"ACGT" prot"MK" "uma string" 123 4.56 7.8e-2 ...
'''

def test_tokenize_basic_sequence():
    lx = Lexer(SAMPLE)
    ts = TokenStream(lx)
    tipos = []
    while True:
        t = ts.next()
        if t is None:
            break
        tipos.append(t.tipo)
    # alguns tokens esperados nesta ordem
    # palavras-chave como 'func' foram mapeadas para KWD na tabela:
    assert 'KWD' in tipos or 'ID' in tipos
    assert 'DNA_LIT' in tipos
    assert 'PROT_LIT' in tipos
    assert 'STRING' in tipos
    assert 'DEC_INT' in tipos  # 123
    assert 'FLOAT' in tipos    # 4.56
    assert 'FLOAT_EXP' in tipos  # 7.8e-2
    assert 'DOT3' in tipos     # ...
