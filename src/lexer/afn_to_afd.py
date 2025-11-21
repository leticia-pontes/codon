from dataclasses import dataclass, field
from typing import Dict, Set, Tuple, List, Optional

@dataclass
class NFAState:
    id: int
    trans: Dict[int, Set[int]] = field(default_factory=dict)
    eps: Set[int] = field(default_factory=set)

@dataclass
class NFA:
    states: Dict[int, NFAState]
    start: int
    accepts: Dict[int, Tuple[str, int]]

class NFABuilder:
    def __init__(self):
        self.next_id = 0
        self.states: Dict[int, NFAState] = {}

    def new_state(self) -> int:
        sid = self.next_id
        self.states[sid] = NFAState(id=sid)
        self.next_id += 1
        return sid

    def add_trans(self, s_from: int, c: int, s_to: int):
        self.states[s_from].trans.setdefault(c, set()).add(s_to)

    def add_trans_set(self, s_from: int, charset: Set[int], s_to: int):
        for c in charset:
            self.add_trans(s_from, c, s_to)

    def add_eps(self, s_from: int, s_to: int):
        self.states[s_from].eps.add(s_to)

    def literal(self, text: str) -> Tuple[int, int]:
        s = self.new_state()
        cur = s
        for ch in text:
            n = self.new_state()
            self.add_trans(cur, ord(ch), n)
            cur = n
        return s, cur

    def charclass(self, charset: Set[int]) -> Tuple[int, int]:
        s = self.new_state()
        t = self.new_state()
        self.add_trans_set(s, charset, t)
        return s, t

    def alt(self, a: Tuple[int, int], b: Tuple[int, int]) -> Tuple[int, int]:
        s = self.new_state()
        t = self.new_state()
        a_start, a_acc = a
        b_start, b_acc = b
        self.add_eps(s, a_start)
        self.add_eps(s, b_start)
        self.add_eps(a_acc, t)
        self.add_eps(b_acc, t)
        return s, t

    def seq(self, a: Tuple[int, int], b: Tuple[int, int]) -> Tuple[int, int]:
        a_start, a_acc = a
        b_start, b_acc = b
        self.add_eps(a_acc, b_start)
        return a_start, b_acc

    def star(self, a: Tuple[int, int]) -> Tuple[int, int]:
        s = self.new_state()
        t = self.new_state()
        a_start, a_acc = a
        self.add_eps(s, a_start)
        self.add_eps(a_acc, t)
        self.add_eps(s, t)
        self.add_eps(a_acc, a_start)
        return s, t

    def plus(self, a: Tuple[int, int]) -> Tuple[int, int]:
        a1 = a
        a2 = self.star(a)
        return self.seq(a1, a2)

    def optional(self, a: Tuple[int, int]) -> Tuple[int, int]:
        s = self.new_state()
        t = self.new_state()
        a_start, a_acc = a
        self.add_eps(s, a_start)
        self.add_eps(s, t)
        self.add_eps(a_acc, t)
        return s, t

ALL_ASCII: Set[int] = set(range(128))
NON_ASCII = 128
ALL_CHARS: Set[int] = set(range(128)) | {NON_ASCII}
DIGITS: Set[int] = set(map(ord, '0123456789'))
UPPER: Set[int] = set(range(ord('A'), ord('Z')+1))
LOWER: Set[int] = set(range(ord('a'), ord('z')+1))
LETTERS: Set[int] = UPPER | LOWER
UNDERSCORE: Set[int] = {ord('_')}
ID_START = LETTERS | UNDERSCORE
ID_CONT  = ID_START | DIGITS
WS_NO_NL = set(map(ord, [' ', '\t', '\f', '\r']))
NL = {ord('\n')}
NOT_QUOTE_NL = ALL_CHARS - {ord('"')} - NL
NOT_NL = ALL_CHARS - NL
SLASH = {ord('/')}
QUOTE = {ord('"')}
PERCENT = {ord('%')}
AMP = {ord('&')}
BAR = {ord('|')}
PLUS = {ord('+')}
MINUS = {ord('-')}
STAR = {ord('*')}
CARET = {ord('^')}
LT = {ord('<')}
GT = {ord('>')}
EQ = {ord('=')}
DOT = {ord('.')}
COMMA = {ord(',')}
SEMI = {ord(';')}
COLON = {ord(':')}
LPAREN = {ord('(')}
RPAREN = {ord(')')}
LBRACE = {ord('{')}
RBRACE = {ord('}')}
LBRACK = {ord('[')}
RBRACK = {ord(']')}
AT = {ord('@')}
BANG = {ord('!')}
TILDE = {ord('~')}
BACKSLASH = {ord('\\')}

def build_token_nfas(builder: NFABuilder):
    token_defs: List[Tuple[Tuple[int,int], str]] = []

    def add(tok_nfa: Tuple[int,int], name: str):
        token_defs.append((tok_nfa, name))

    s1 = builder.seq(builder.literal('/"'), builder.star(builder.charclass(NOT_NL)))
    add(s1, 'LINE_COMMENT')
    s1b = builder.seq(builder.literal('//'), builder.star(builder.charclass(NOT_NL)))
    add(s1b, 'LINE_COMMENT2')

    s, a = builder.literal('"""')
    A = a
    x = builder.charclass(ALL_CHARS - {ord('"')})
    builder.add_eps(A, x[0])
    builder.add_eps(x[1], A)
    B_start, B_acc = builder.literal('"')
    builder.add_eps(A, B_start)
    C_start, C_acc = builder.literal('"')
    y = builder.charclass(ALL_CHARS - {ord('"')})
    builder.add_eps(B_acc, C_start)
    builder.add_eps(B_acc, y[0])
    builder.add_eps(y[1], A)
    end = builder.new_state()
    builder.add_trans(C_acc, ord('"'), end)
    z = builder.charclass(ALL_CHARS - {ord('"')})
    builder.add_eps(C_acc, z[0])
    builder.add_eps(z[1], A)
    add((s, end), 'BLOCK_COMMENT')

    add(builder.plus(builder.charclass(WS_NO_NL)), 'WS')
    add(builder.charclass(NL), 'NEWLINE')

    for lex, name in [
        ('...', 'DOT3'), ('..', 'DOT2'),
        ('=>', 'FATARROW'), ('->', 'ARROW'),
        ('<<=', 'SHL_EQ'), ('>>=', 'SHR_EQ'),
        ('<<', 'SHL'), ('>>', 'SHR'),
        ('+=', 'PLUS_EQ'), ('-=', 'MINUS_EQ'), ('*=', 'STAR_EQ'),
        ('/=', 'SLASH_EQ'), ('%=', 'PERC_EQ'),
        ('==', 'EQ'), ('!=', 'NE'),
        ('<=', 'LE'), ('>=', 'GE'),
        ('&&', 'AND_AND'), ('||', 'OR_OR'),
    ]:
        add(builder.literal(lex), name)

    def quoted_payload():
        body_unit = builder.alt(
            builder.seq(builder.charclass(BACKSLASH), builder.charclass(ALL_ASCII)),
            builder.charclass(NOT_QUOTE_NL)
        )
        return builder.star(body_unit)

    for prefix, name in [('dna"', 'DNA_LIT'), ('rna"', 'RNA_LIT'), ('prot"', 'PROT_LIT')]:
        p = builder.literal(prefix)
        pay = quoted_payload()
        close = builder.literal('"')
        add(builder.seq(builder.seq(p, pay), close), name)

    openq = builder.literal('"')
    payload = quoted_payload()
    closeq = builder.literal('"')
    add(builder.seq(builder.seq(openq, payload), closeq), 'STRING')

    dplus = builder.plus(builder.charclass(DIGITS))
    dot = builder.charclass(DOT)
    frac = builder.plus(builder.charclass(DIGITS))
    opt_frac = builder.optional(builder.seq(dot, frac))
    eE = builder.charclass(set(map(ord, 'eE')))
    sign = builder.optional(builder.charclass(set(map(ord, '+-'))))
    exp = builder.seq(eE, builder.seq(sign, builder.plus(builder.charclass(DIGITS))))
    float_exp = builder.seq(dplus, builder.seq(opt_frac, exp))
    add(float_exp, 'FLOAT_EXP')

    float_simple = builder.seq(dplus, builder.seq(dot, frac))
    add(float_simple, 'FLOAT')

    add(dplus, 'DEC_INT')

    id_start = builder.charclass(ID_START)
    id_cont = builder.star(builder.charclass(ID_CONT))
    add(builder.seq(id_start, id_cont), 'ID')

    for (charset, name) in [
        (LPAREN, 'LPAREN'), (RPAREN, 'RPAREN'),
        (LBRACE, 'LBRACE'), (RBRACE, 'RBRACE'),
        (LBRACK, 'LBRACK'), (RBRACK, 'RBRACK'),
        (COMMA, 'COMMA'), (SEMI, 'SEMI'), (COLON, 'COLON'),
        (AT, 'AT'),
        (PLUS, 'PLUS'), (MINUS, 'MINUS'), (STAR, 'STAR'), (SLASH, 'SLASH'),
        (PERCENT, 'PERCENT'), (CARET, 'CARET'),
        (AMP, 'AMP'), (BAR, 'BAR'),
        (BANG, 'BANG'), (TILDE, 'TILDE'),
        (EQ, 'ASSIGN'), (LT, 'LT'), (GT, 'GT'),
        (DOT, 'DOT'),
    ]:
        add(builder.charclass(charset), name)

    nfas_with_meta: List[Tuple[int,int,str,int]] = []
    for prio, (pair, name) in enumerate(token_defs):
        nfas_with_meta.append((pair[0], pair[1], name, prio))
    return token_defs

def merge_nfas_to_master(token_defs: List[Tuple[Tuple[int,int], str]]) -> NFA:
    raise NotImplementedError("merge_nfas_to_master é injetado pelo construtor externo.")

@dataclass(frozen=True)
class DFAStateKey:
    nfa_states: Tuple[int, ...]

@dataclass
class DFA:
    start: int
    accepts: Dict[int, Tuple[str, int]]
    trans: Dict[int, Dict[int, int]]

def epsilon_closure(states: Set[int], nfa: NFA) -> Set[int]:
    stack = list(states)
    closure = set(states)
    while stack:
        s = stack.pop()
        for t in nfa.states[s].eps:
            if t not in closure:
                closure.add(t)
                stack.append(t)
    return closure

def move(states: Set[int], c: int, nfa: NFA) -> Set[int]:
    dest = set()
    for s in states:
        if c in nfa.states[s].trans:
            dest |= nfa.states[s].trans[c]
    return dest

def build_dfa(nfa: NFA, alphabet: List[int]) -> DFA:
    key_to_id: Dict[DFAStateKey, int] = {}
    dfa_trans: Dict[int, Dict[int, int]] = {}
    dfa_accepts: Dict[int, Tuple[str, int]] = {}

    start_cl = epsilon_closure({nfa.start}, nfa)
    start_key = DFAStateKey(tuple(sorted(start_cl)))
    key_to_id[start_key] = 0
    worklist = [start_key]

    def pick_accept(nfa_states: Set[int]) -> Optional[Tuple[str, int]]:
        best: Optional[Tuple[str, int]] = None
        for s in nfa_states:
            if s in nfa.accepts:
                tok, pr = nfa.accepts[s]
                if (best is None) or (pr < best[1]):
                    best = (tok, pr)
        return best

    acc = pick_accept(set(start_cl))
    if acc:
        dfa_accepts[0] = acc

    while worklist:
        key = worklist.pop()
        sid = key_to_id[key]
        cur_set = set(key.nfa_states)
        dfa_trans.setdefault(sid, {})
        for c in alphabet:
            m = move(cur_set, c, nfa)
            if not m:
                continue
            cl = epsilon_closure(m, nfa)
            new_key = DFAStateKey(tuple(sorted(cl)))
            if new_key not in key_to_id:
                key_to_id[new_key] = len(key_to_id)
                acc2 = pick_accept(cl)
                if acc2:
                    dfa_accepts[key_to_id[new_key]] = acc2
                worklist.append(new_key)
            dfa_trans[sid][c] = key_to_id[new_key]

    return DFA(start=0, accepts=dfa_accepts, trans=dfa_trans)

def merge_nfas_to_master(token_defs: List[Tuple[Tuple[int, int], str]], builder: NFABuilder) -> NFA:
    """
    Combina uma lista de NFAs de tokens individuais em um único NFA mestre
    com um novo estado inicial e priorização por ordem.
    """
    start = builder.new_state()
    accepts: Dict[int, Tuple[str, int]] = {}

    for prio, (pair, name) in enumerate(token_defs):
        s, a = pair
        builder.add_eps(start, s)
        accepts[a] = (name, prio)

    return NFA(states=builder.states, start=start, accepts=accepts)

def build_master_dfa():
    builder = NFABuilder()
    token_defs = build_token_nfas(builder)
    nfa = merge_nfas_to_master(token_defs, builder)
    alphabet = list(range(129))
    dfa = build_dfa(nfa, alphabet)
    return dfa

def compress_dfa(dfa: DFA) -> Dict[str, object]:
    return {
        "start": dfa.start,
        "accepts": {int(k): (v[0], int(v[1])) for k, v in dfa.accepts.items()},
        "trans": {int(s): {int(c): int(t) for c, t in row.items()} for s, row in dfa.trans.items()},
    }

if __name__ == "__main__":
    dfa = build_master_dfa()
    data = compress_dfa(dfa)
    import json, sys
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
