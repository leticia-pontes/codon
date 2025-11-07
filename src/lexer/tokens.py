from dataclasses import dataclass
from typing import Any, List

# Lista de Palavras-Chave (KWD)
KEYWORDS = {
    "and", "or", "not", "if", "else", "for", "while", "return",
    "break", "continue", "function", "var", "const", "import", "from", "as",
    "struct", "enum", "match", "case", "default", "true", "false", "null",
    "pub", "extern", "use",
    "void", "read", "print", "new"
}

TOKEN_KINDS = {
    # Ignorados (serão filtrados no Lexer)
    'WS', 'NEWLINE', 'LINE_COMMENT', 'BLOCK_COMMENT',
    # Delimitadores Compostos (Prioridade de Maximal-Munch)
    'DOT3', 'DOT2', 'FATARROW', 'ARROW',
    # Operadores Compostos
    'SHR_EQ', 'SHL_EQ', 'PLUS_EQ', 'MINUS_EQ', 'STAR_EQ', 'SLASH_EQ',
    'PERC_EQ', 'AMP_EQ', 'BAR_EQ', 'CARET_EQ', 'EQ', 'NE', 'LE', 'GE',
    'AND_AND', 'OR_OR', 'SHR', 'SHL',
    # Delimitadores Simples
    'LPAREN', 'RPAREN', 'LBRACE', 'RBRACE', 'LBRACK', 'RBRACK',
    'COMMA', 'SEMI', 'COLON', 'AT', 'DOT',
    # Operadores Simples (incluídos na seção de delimitadores na especificação)
    'PLUS', 'MINUS', 'STAR', 'SLASH', 'PERCENT', 'CARET', 'AMP', 'BAR', 'BANG', 'TILDE', 'ASSIGN', 'LT', 'GT',
    # Literais (Strings e Biológicos)
    'STRING', 'CHAR', 'TRIPLE_STRING', 'BYTE_STRING', 'RAW_STRING',
    'DNA_LIT', 'RNA_LIT', 'PROT_LIT',
    # Números
    'DEC_INT', 'HEX_INT', 'OCT_INT', 'BIN_INT', 'FLOAT', 'FLOAT_EXP', 'INF_NAN',
    # Identificadores e Palavras-chave
    'KWD', 'ID',
    # Especiais
    'EOF', 'UNKNOWN'
}


@dataclass
class Token:
    """Representação de um Token."""
    kind: str
    lexeme: str
    literal: Any
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.kind}, '{self.lexeme}', L{self.line}:C{self.col})"

class TokenStream:
    """Stream de tokens com capacidades de peek/expect para o Parser."""
    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._current = 0

    def peek(self, offset: int = 0) -> Token:
        """Retorna o token atual ou futuro sem consumir."""
        index = self._current + offset
        if index >= len(self._tokens):
            return Token('EOF', '', None, self._tokens[-1].line if self._tokens else 1, self._tokens[-1].col if self._tokens else 1)
        return self._tokens[index]

    def current(self) -> Token:
        """Retorna o token que acabou de ser consumido."""
        if self._current == 0:
            return self.peek(0) # Retorna o primeiro se ainda não avançou
        return self._tokens[self._current - 1]

    def next(self) -> Token:
        """Consome e retorna o próximo token."""
        token = self.peek()
        if token.kind != 'EOF':
            self._current += 1
        return token

    def accept(self, *expected_kinds: str) -> bool:
        """Consome o token se o tipo casar com um dos esperados."""
        if self.peek().kind in expected_kinds:
            self.next()
            return True
        return False

    def expect(self, expected_kind: str, expected_lexeme: str = None) -> Token:
        """Consome o token ou lança SyntaxError."""
        token = self.peek()
        if token.kind == expected_kind and (expected_lexeme is None or token.lexeme == expected_lexeme):
            self.next()
            return token

        from ...utils.erros import SyntaxError

        expected_info = f"'{expected_lexeme}'" if expected_lexeme else expected_kind
        raise SyntaxError(f"Esperado {expected_info}, mas chegou '{token.lexeme}' ({token.kind}).", token.line, token.col)