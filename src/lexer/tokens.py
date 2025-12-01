from dataclasses import dataclass
from typing import Any, List

# Lista de Palavras-Chave (KWD)
KEYWORDS = {
    "and", "or", "not", "if", "else", "elif", "for", "while", "loop", "return",
    "break", "continue", "function", "procedure", "var", "const", "import", "from", "as",
    "struct", "enum", "match", "case", "default", "true", "false", "null",
    "pub", "extern", "use", "class", "extends",
    "void", "read", "print", "new", "int", "float", "double", "string", "bool", "char"
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
    """
    Representação de um Token.
    CORRIGIDO: kind -> tipo, lexeme -> valor, line -> linha, col -> coluna.
    """
    tipo: str # Antigo: kind
    valor: str # Antigo: lexeme
    literal: Any
    linha: int # Antigo: line
    coluna: int # Antigo: col

    def __repr__(self):
        # CORRIGIDO: Usando os novos nomes de atributos
        return f"Token({self.tipo}, '{self.valor}', L{self.linha}:C{self.coluna})"

class TokenStream:
    """Stream de tokens com capacidades de peek/expect para o Parser."""
    def __init__(self, tokens: List[Token]):
        self._tokens = tokens
        self._current = 0

    def peek(self, offset: int = 0) -> Token:
        """Retorna o token atual ou futuro sem consumir."""
        index = self._current + offset
        if index >= len(self._tokens):
            # CORRIGIDO: Criação do EOF usando .linha e .coluna do último token
            ultimo_token = self._tokens[-1] if self._tokens else None
            linha_eof = ultimo_token.linha if ultimo_token else 1
            coluna_eof = ultimo_token.coluna if ultimo_token else 1
            return Token('EOF', '', None, linha_eof, coluna_eof)
        return self._tokens[index]

    def current(self) -> Token:
        """Retorna o token que acabou de ser consumido."""
        if self._current == 0:
            return self.peek(0) # Retorna o primeiro se ainda não avançou
        return self._tokens[self._current - 1]

    def next(self) -> Token:
        """Consome e retorna o próximo token."""
        token = self.peek()
        # CORRIGIDO: Usando token.tipo (antigo .kind)
        if token.tipo != 'EOF':
            self._current += 1
        return token

    def accept(self, *expected_kinds: str) -> bool:
        """Consome o token se o tipo casar com um dos esperados."""
        # CORRIGIDO: Usando self.peek().tipo (antigo .kind)
        if self.peek().tipo in expected_kinds:
            self.next()
            return True
        return False

    def expect(self, expected_kind: str, expected_lexeme: str = None) -> Token:
        """Consome o token ou lança SyntaxError."""
        token = self.peek()

        # CORRIGIDO: Usando token.tipo (antigo .kind) e token.valor (antigo .lexeme)
        if token.tipo == expected_kind and (expected_lexeme is None or token.valor == expected_lexeme):
            self.next()
            return token

        from ...utils.erros import SyntaxError

        expected_info = f"'{expected_lexeme}'" if expected_lexeme else expected_kind

        # CORRIGIDO: Usando token.valor, token.tipo, token.linha e token.coluna
        raise SyntaxError(f"Esperado {expected_info}, mas chegou '{token.valor}' ({token.tipo}).", token.linha, token.coluna)