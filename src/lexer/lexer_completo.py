from dataclasses import dataclass
from typing import Optional, List, Tuple, Deque, Iterator
from collections import deque
import re

# ---------------
# Token dataclass
# ---------------
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

# ------
# Regras
# ------
REGRAS = [
    # Comentários / espaços (None = token ignorado)
    (r'"""([\s\S]*?)"""', None),        # BLOCK_COMMENT (não-guloso)
    (r'/"[^\n]*', None),                # LINE_COMMENT que começa com /"
    (r'//[^\n]*', None),                # LINE_COMMENT // até o fim da linha
    (r'[\t\f\r ]+', None),              # WS
    (r'\n', None),                      # NEWLINE (será usado apenas para manutenção de linha/col)

    # Operadores compostos e tokens que exigem priorização (mais longos primeiro por regra)
    (r'\.\.\.', 'DOT3'),
    (r'\.\.', 'DOT2'),
    (r'=>', 'FATARROW'),
    (r'->', 'ARROW'),
    (r'<<=', 'SHL_EQ'),
    (r'>>=', 'SHR_EQ'),
    (r'<<', 'SHL'),
    (r'>>', 'SHR'),
    (r'\+=', 'PLUS_EQ'),
    (r'-=', 'MINUS_EQ'),
    (r'\*=', 'STAR_EQ'),
    (r'/=', 'SLASH_EQ'),
    (r'%=', 'PERC_EQ'),
    (r'==', 'EQ'),
    (r'!=', 'NE'),
    (r'<=', 'LE'),
    (r'>=', 'GE'),
    (r'&&', 'AND_AND'),
    (r'\|\|', 'OR_OR'),

    # Literais biológicos / strings
    (r'dna"(\\"|[^"])*"', 'DNA_LIT'),
    (r'rna"(\\"|[^"])*"', 'RNA_LIT'),
    (r'prot"(\\"|[^"])*"', 'PROT_LIT'),
    (r'"(\\.|[^"\n])*"', 'STRING'),  # aceita escapes e evita incluir nova linha

    # Numeros
    (r'\d+(\.\d+)?([eE][+-]?\d+)', 'FLOAT_EXP'),
    (r'\d+\.\d+', 'FLOAT'),
    (r'\d+', 'DEC_INT'),

    # Identificadores e keywords (keywords serão resolvidas depois)
    (r'[A-Za-z_][A-Za-z0-9_]*', 'ID'),

    # Operadores simples e delimitadores
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

# Palavras-chave
PALAVRAS_CHAVE = {
    "and": "KWD", "or": "KWD", "not": "KWD",
    "if": "KWD", "else": "KWD", "for": "KWD",
    "while": "KWD", "return": "KWD", "break": "KWD",
    "continue": "KWD", "func": "KWD", "var": "KWD",
    "const": "KWD", "import": "KWD", "from": "KWD",
    "as": "KWD", "struct": "KWD", "enum": "KWD",
    "match": "KWD", "case": "KWD", "default": "KWD",
    "true": "KWD", "false": "KWD", "null": "KWD",
    "pub": "KWD", "extern": "KWD", "use": "KWD",
    "int": "KWD", "float": "KWD", "bool": "KWD",
    "string": "KWD", "dna": "KWD", "rna": "KWD",
    "prot": "KWD", "void": "KWD"
}

# Compilação das regexes (mantendo a ordem para desempate)
_compiled_rules = [(re.compile(r), t) for r, t in REGRAS]


# -----------------------------------------
# Lexer com match mais longo + bufferização
# -----------------------------------------
class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.length = len(source)
        self.pos = 0
        self.linha = 1
        self.coluna = 1
        self._buf: Deque[Token] = deque()  # buffer para lookahead / pushback

    def _update_line_col(self, text: str):
        """Atualiza linha/coluna ao consumir texto."""
        lines = text.splitlines(keepends=True)
        if not lines:
            return
        if len(lines) == 1:
            self.coluna += len(text)
        else:
            # há quebras de linha
            for ch in text:
                if ch == '\n':
                    self.linha += 1
                    self.coluna = 1
                else:
                    self.coluna += 1

    def _longest_match_at(self, pos: int) -> Optional[Tuple[re.Match, str, int]]:
        """
        Tenta todas as regras no ponto `pos` e retorna:
           (match_obj, token_tipo, regra_index)
        que corresponde ao comprimento máximo. Em empate, menor regra_index (mais cedo na lista) vence.
        """
        best = None  # (match, tipo, idx)
        for idx, (regex, t_tipo) in enumerate(_compiled_rules):
            m = regex.match(self.source, pos)
            if not m:
                continue
            length = m.end() - m.start()
            if length == 0:
                continue
            if best is None:
                best = (m, t_tipo, idx)
            else:
                cur_len = best[0].end() - best[0].start()
                if length > cur_len:
                    best = (m, t_tipo, idx)
                elif length == cur_len:
                    # desempate: ordem da regra (menor idx) mantém prioridade
                    if idx < best[2]:
                        best = (m, t_tipo, idx)
        return best

    def _next_token_internal(self) -> Optional[Token]:
        if self.pos >= self.length:
            return None
        res = self._longest_match_at(self.pos)
        if res is None:
            # Erro léxico: caractere não reconhecido
            bad_char = self.source[self.pos]
            raise LexicalError(f"Caractere não reconhecido '{bad_char}'", self.linha, self.coluna)
        m, token_tipo, rule_idx = res
        valor = m.group(0)
        start_pos = m.start()
        end_pos = m.end()
        token_line = self.linha
        token_col = self.coluna

        # Avança posição e atualiza linha/coluna
        self.pos = end_pos
        self._update_line_col(valor)

        # Token ignorado (comentários e espaços)
        if token_tipo is None:
            return self._next_token_internal()

        if token_tipo == 'ID' and valor in PALAVRAS_CHAVE:
            token_tipo = PALAVRAS_CHAVE[valor]

        return Token(token_tipo, valor, token_line, token_col, start_pos, end_pos)

    # API pública

    def next(self) -> Optional[Token]:
        """Retorna o próximo token (consumido)."""
        if self._buf:
            return self._buf.popleft()
        t = self._next_token_internal()
        return t

    def peek(self, n: int = 1) -> List[Optional[Token]]:
        """Retorna até n tokens olhando à frente, sem consumir."""
        # Preenche buffer até ter n tokens
        while len(self._buf) < n:
            t = self._next_token_internal()
            if t is None:
                break
            self._buf.append(t)
        # Retorna cópias (não necessárias se imutável); OK retornar referências
        return [self._buf[i] if i < len(self._buf) else None for i in range(n)]

    def push_back(self, token: Token):
        """Coloca um token de volta no início do stream (pushback)."""
        self._buf.appendleft(token)

    def tokenize_all(self) -> List[Token]:
        """Consume and return all tokens (útil para testes)."""
        toks = []
        while True:
            t = self.next()
            if t is None:
                break
            toks.append(t)
        return toks

class LexicalError(Exception):
    def __init__(self, msg: str, linha: int, coluna: int):
        super().__init__(f"{msg} (Linha {linha}, Coluna {coluna})")
        self.linha = linha
        self.coluna = coluna

# ----------------------------------------------
# Helper para parser: TokenStream / ParserHelper
# ----------------------------------------------
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
        return self.buffer[n-1] if len(self.buffer) >= n else None

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

# -----------------------------
# Exemplo de uso / teste rápido
# -----------------------------
if __name__ == "__main__":
    exemplo = r'''
    // comentário simples
    func soma(a, b) {
      return a + b;
    }

    dna"ACGT" prot"MK" "uma string" 123 4.56 7.8e-2 ...
    '''
    lx = Lexer(exemplo)
    ts = TokenStream(lx)
    print("Tokens:")
    try:
        while True:
            t = ts.next()
            if t is None:
                break
            print(t)
    except LexicalError as e:
        print("Erro léxico:", e)
