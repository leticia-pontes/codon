from dataclasses import dataclass
from typing import Optional, List, Tuple, Deque
from collections import deque
import re

from src.utils.erros import ErrorHandler, LexicalError

# --------------- Regras e palavras-chave ---------------

REGRAS = [
    (r'/"[\s\S]*?"/', None),
    (r'//[^\n]*', None),
    (r'[\t\f\r ]+', None),
    (r'\n', None),

    (r'<-', 'ARROW_LEFT'),
    (r'->', 'ARROW_RIGHT'),
    (r'\.\.\.', 'DOT3'),
    (r'\.\.', 'DOT2'),
    (r'=>', 'FATARROW'),
    (r'<<=', 'SHL_EQ'),
    (r'>>=', 'SHR_EQ'),
    (r'<<', 'SHL'),
    (r'>>', 'SHR'),
    (r'\+=', 'PLUS_EQ'),
    (r'-=', 'MINUS_EQ'),
    (r'\+\+', 'PLUS_PLUS'),
    (r'--', 'MINUS_MINUS'),
    (r'\*=', 'STAR_EQ'),
    (r'/=', 'SLASH_EQ'),
    (r'%=', 'PERC_EQ'),
    (r'==', 'EQ'),
    (r'!=', 'NE'),
    (r'<=', 'LE'),
    (r'>=', 'GE'),
    (r'&&', 'AND_AND'),
    (r'\|\|', 'OR_OR'),

    (r'dna"(\\"|[^"])*"', 'DNA_LIT'),
    (r'rna"(\\"|[^"])*"', 'RNA_LIT'),
    (r'prot"(\\"|[^"])*"', 'PROT_LIT'),
    (r'"(\\.|[^"\n])*"', 'STRING'),

    (r"'(\\.|[^'\\n])'", "CHAR_LIT"),

    (r'\d+\.\d+[eE][+-]?\d+', 'FLOAT_EXP'),
    (r'\d+[eE][+-]?\d+', 'FLOAT_EXP'),
    (r'\d+\.\d+', 'FLOAT'),
    (r'\d+', 'DEC_INT'),

    (r'[A-Za-z_][A-Za-z0-9_]*', 'ID'),

    (r'=', 'ASSIGN'),
    (r'\+', 'PLUS'),
    (r'-', 'MINUS'),
    (r'\*', 'STAR'),
    (r'/', 'SLASH'),
    (r'%', 'PERCENT'),
    (r'\^', 'CARET'),
    (r'>', 'GT'),
    (r'<', 'LT'),
    (r'&', 'AMP'),
    (r'\|', 'BAR'),
    (r'!', 'BANG'),
    (r'~', 'TILDE'),
    (r'\(', 'LPAREN'),
    (r'\)', 'RPAREN'),
    (r'\{', 'LBRACE'),
    (r'\}', 'RBRACE'),
    (r'\[', 'LBRACK'),
    (r'\]', 'RBRACK'),
    (r';', 'SEMI'),
    (r':', 'COLON'),
    (r',', 'COMMA'),
    (r'\.', 'DOT'),
]

PALAVRAS_CHAVE = {
    "and": "KWD", "or": "KWD", "not": "KWD",
    "if": "KWD", "elif": "KWD", "else": "KWD", "while": "KWD", "for": "KWD",
    "switch": "KWD", "case": "KWD", "return": "KWD", "break": "KWD",
    "continue": "KWD", "function": "KWD", "procedure": "KWD", "var": "KWD",
    "const": "KWD", "import": "KWD", "from": "KWD", "as": "KWD", "struct": "KWD",
    "enum": "KWD", "match": "KWD", "default": "KWD", "true": "KWD", "false": "KWD",
    "null": "KWD", "pub": "KWD", "extern": "KWD", "use": "KWD", "class": "KWD",
    "int": "KWD", "decimal": "KWD", "bool": "KWD", "string": "KWD", "list": "KWD",
    "vector": "KWD", "Nbase": "KWD", "void": "KWD", "print": "KWD", "Dbase": "KWD", "Rbase": "KWD",
    "new": "KWD",
    "extends": "KWD"
}

_compiled_rules = [(re.compile(r), t) for r, t in REGRAS]

@dataclass
class Token:
    tipo: str
    valor: str
    linha: int
    coluna: int
    start_pos: int
    end_pos: int

    def __repr__(self):
        return f"Token({self.tipo!r}, {self.valor!r}, Ln{self.linha}, Col{self.coluna})"

    def __hash__(self):
        return hash((self.tipo, self.valor, self.linha, self.coluna))


class Lexer:
    def __init__(self, source: str, error_handler=None):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.linha = 1
        self.coluna = 1
        self._buf: Deque[Token] = deque()
        self.error_handler = error_handler or ErrorHandler()

    def _update_line_col(self, text: str):
        if not text:
            return
        last_newline = text.rfind('\n')
        if last_newline != -1:
            # atualiza linhas e coloca coluna como número de chars após a última newline
            self.linha += text.count('\n')
            # posição dentro da última linha (1-based)
            self.coluna = len(text) - last_newline - 1
        else:
            self.coluna += len(text)

    def _longest_match_at(self, pos: int) -> Optional[Tuple[re.Match, str, int]]:
        best = None
        for idx, (regex, t_tipo) in enumerate(_compiled_rules):
            m = regex.match(self.source, pos)
            if not m:
                continue
            length = m.end() - m.start()
            if length == 0:
                continue
            if best is None or length > (best[0].end() - best[0].start()) or (
                length == (best[0].end() - best[0].start()) and idx < best[2]
            ):
                best = (m, t_tipo, idx)
        return best

    def _next_token_internal(self) -> Optional[Token]:
        # loop para pular caracteres inválidos sem encerrar a tokenização
        while self.pos < self.length:
            start_pos_current = self.pos
            start_line_current = self.linha
            start_col_current = self.coluna

            res = self._longest_match_at(start_pos_current)
            if res is None:
                bad_char = self.source[self.pos]
                self.pos += 1
                self._update_line_col(bad_char)

                err = LexicalError(f"Caractere não reconhecido '{bad_char}'", start_line_current, start_col_current)
                self.error_handler.report_error(err)

                # continuar o laço para tentar o próximo caractere/token
                continue

            m, token_tipo, rule_idx = res
            valor = m.group(0)
            end_pos = m.end()
            self.pos = end_pos
            self._update_line_col(valor)

            if token_tipo is None:
                # token descartável (comentário / whitespace) - continuar
                continue

            if token_tipo == 'ID' and valor in PALAVRAS_CHAVE:
                token_tipo = PALAVRAS_CHAVE[valor]

            return Token(token_tipo, valor, start_line_current, start_col_current, start_pos_current, end_pos)

        # EOF
        return None

    def next(self) -> Optional[Token]:
        if self._buf:
            return self._buf.popleft()
        return self._next_token_internal()

    def peek(self, n: int = 1) -> Optional[Token]:
        while len(self._buf) < n:
            t = self._next_token_internal()
            if t is None:
                break
            self._buf.append(t)
        return self._buf[n - 1] if len(self._buf) >= n else None

    def push_back(self, token: Token):
        self._buf.appendleft(token)

    def tokenize_all(self) -> List[Token]:
        toks = []
        while True:
            t = self.next()
            if t is None:
                break
            toks.append(t)
        return toks


class TokenStream:
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.buffer: Deque[Token] = deque()

    def _fill(self, n: int):
        while len(self.buffer) < n:
            t = self.lexer.next()
            if t is None:
                break
            self.buffer.append(t)

    def peek(self, n: int = 1) -> Optional[Token]:
        self._fill(n)
        return self.buffer[n - 1] if len(self.buffer) >= n else None

    def next(self) -> Optional[Token]:
        if self.buffer:
            return self.buffer.popleft()
        return self.lexer.next()

    def accept(self, tipo: str) -> Optional[Token]:
        t = self.peek(1)
        if t and t.tipo == tipo:
            return self.next()
        return None

    def expect(self, tipo: str) -> Token:
        t = self.next()
        if t is None:
            raise SyntaxError(f"Esperado token {tipo}, mas chegou EOF")
        if t.tipo != tipo:
            raise SyntaxError(f"Esperado token {tipo}, mas chegou {t.tipo} em Ln{t.linha} Col{t.coluna}")
        return t

    def match(self, *tipos: str) -> Optional[Token]:
        t = self.peek(1)
        if t and t.tipo in tipos:
            return self.next()
        return None

    def push_back(self, token: Token):
        self.buffer.appendleft(token)
