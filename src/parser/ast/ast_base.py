from typing import List
from ..lexer.tokens import Token

class ASTNode:
    def __init__(self, token: Token):
        self.token = token

    def __repr__(self):
        return f"{self.__class__.__name__}"

class Program(ASTNode):
    def __init__(self, token: Token, statements: List['Declaration']):
        super().__init__(token)
        self.statements = statements

class Declaration(ASTNode):
    pass # Base para VarDecl, FunctionDecl, etc.

class Statement(Declaration):
    pass # Base para IfStmt, WhileStmt, ExprStmt, etc.

class Expression(ASTNode):
    pass # Base para Binary, Unary, Literal, etc.