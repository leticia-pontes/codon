import pytest
from src.lexer.analisador_lexico_completo import Lexer, LexicalError

def test_lexer_raises_on_invalid_char():
    # caractere inválido (por exemplo, caractere unicode não esperado/ símbolo raro)
    src = 'func x = 10\n$'   # $ inválido
    lx = Lexer(src)
    with pytest.raises(LexicalError):
        # consumir tokens até o erro
        while True:
            t = lx.next()
            if t is None:
                break
