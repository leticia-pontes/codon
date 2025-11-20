from typing import List, Optional, Any
from .ast_base import ASTNode
from ...lexer.tokens import Token

# --- Expressões ---

class Binary(ASTNode):
    """Expressão Binária: left Op right (ex: a + b)"""
    def __init__(self, token: Token, left: ASTNode, operator: Token, right: ASTNode):
        super().__init__(token)
        self.left = left
        self.operator = operator
        self.right = right

class Unary(ASTNode):
    """Expressão Unária: Op right (ex: -a, !a)"""
    def __init__(self, token: Token, operator: Token, right: ASTNode):
        super().__init__(token)
        self.operator = operator
        self.right = right

class Literal(ASTNode):
    """Literal: Número, String, Booleanos, Literais Biológicos"""
    def __init__(self, token: Token, value: Any):
        super().__init__(token)
        self.value = value

class Grouping(ASTNode):
    """Agrupamento por Parênteses: (Expression)"""
    def __init__(self, token: Token, expression: ASTNode):
        super().__init__(token)
        self.expression = expression

class Identifier(ASTNode):
    """Referência a um Identificador (Variável, Parâmetro)"""
    def __init__(self, token: Token, name: str):
        super().__init__(token)
        self.name = name

class Assignment(ASTNode):
    """Atribuição (Assignment): Designador OpAtrib Value"""
    def __init__(self, token: Token, target: ASTNode, value: ASTNode):
        super().__init__(token)
        self.target = target
        self.value = value

class Call(ASTNode):
    """Chamada de Função/Método (Call): Designador ( ParamsAtivosOpt )"""
    def __init__(self, token: Token, callee: ASTNode, arguments: List[ASTNode]):
        super().__init__(token)
        self.callee = callee
        self.arguments = arguments

class IndexAccess(ASTNode):
    """Acesso a Índice: Designador [ Expressao ]"""
    def __init__(self, token: Token, container: ASTNode, index: ASTNode):
        super().__init__(token)
        self.container = container
        self.index = index

class MemberAccess(ASTNode):
    """Acesso a Membro: Designador . Ident"""
    def __init__(self, token: Token, container: ASTNode, member: Token):
        super().__init__(token)
        self.container = container
        self.member = member

# --- Classes que implementam o Designador da EBNF/BNF ---

class Designator(ASTNode):
    """
    Designador: Ident { "." Ident | "[" Expressao "]" }
    Esta classe base é usada apenas para facilitar a distinção no parser.
    Na AST, os acessos são representados por MemberAccess/IndexAccess encadeados.
    """
    # O Designator não tem um construtor próprio aqui, então herdar de ASTNode
    # é mais seguro se ele for apenas uma classe marcadora.
    pass