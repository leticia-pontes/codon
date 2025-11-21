from typing import List, Optional
from .ast_base import Expression
from ..lexer.tokens import Token

# --- Expressões ---

class Binary(Expression):
    """Expressão Binária: left Op right (ex: a + b)"""
    def __init__(self, token: Token, left: Expression, operator: Token, right: Expression):
        super().__init__(token)
        self.left = left
        self.operator = operator
        self.right = right

class Unary(Expression):
    """Expressão Unária: Op right (ex: -a, !a)"""
    def __init__(self, token: Token, operator: Token, right: Expression):
        super().__init__(token)
        self.operator = operator
        self.right = right

class Literal(Expression):
    """Literal: Número, String, Booleanos, Literais Biológicos"""
    def __init__(self, token: Token, value: Any):
        super().__init__(token)
        self.value = value

class Grouping(Expression):
    """Agrupamento por Parênteses: (Expression)"""
    def __init__(self, token: Token, expression: Expression):
        super().__init__(token)
        self.expression = expression

class Identifier(Expression):
    """Referência a um Identificador (Variável, Parâmetro)"""
    def __init__(self, token: Token, name: str):
        super().__init__(token)
        self.name = name

class Assignment(Expression):
    """Atribuição (Assignment): Designador OpAtrib Value"""
    def __init__(self, token: Token, target: Expression, value: Expression):
        super().__init__(token)
        self.target = target # Pode ser Identifier, IndexAccess, MemberAccess
        self.value = value

class Call(Expression):
    """Chamada de Função/Método (Call): Designador ( ParamsAtivosOpt )"""
    def __init__(self, token: Token, callee: Expression, arguments: List[Expression]):
        super().__init__(token)
        self.callee = callee
        self.arguments = arguments

class IndexAccess(Expression):
    """Acesso a Índice: Designador [ Expressao ]"""
    def __init__(self, token: Token, container: Expression, index: Expression):
        super().__init__(token)
        self.container = container
        self.index = index

class MemberAccess(Expression):
    """Acesso a Membro: Designador . Ident"""
    def __init__(self, token: Token, container: Expression, member: Token):
        super().__init__(token)
        self.container = container
        self.member = member

# --- Classes que implementam o Designador da EBNF/BNF ---
# Designador é o prefixo de acesso (Ident, MemberAccess, IndexAccess)

class Designator(Identifier):
    """
    Designador: Ident { "." Ident | "[" Expressao "]" }
    Esta classe base é usada apenas para facilitar a distinção no parser.
    Na AST, os acessos são representados por MemberAccess/IndexAccess encadeados.
    """
    pass