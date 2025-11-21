from typing import List, Optional
from .ast_base import Statement, Declaration, Expression, Block
from ..lexer.tokens import Token # Importa Token para referência de tipo

# --- Declarações ---

class VarDecl(Declaration):
    """Corresponde a DeclVar na EBNF: var Tipo Ident { "," Ident } ";" """
    def __init__(self, token: Token, identifier: Token, var_type: str, initial_value: Optional[Expression], is_mutable: bool = True):
        super().__init__(token)
        self.identifier = identifier
        self.var_type = var_type # Deve ser o Ident que define o tipo
        self.initial_value = initial_value
        self.is_mutable = is_mutable

class FunctionDecl(Declaration):
    """Corresponde a DeclMetodo na EBNF: void Ident "(" ParamsFormOpt ")" ... Bloco"""
    def __init__(self, token: Token, name: Token, params: List['Parameter'], body: 'Block', return_type: str = 'void'):
        super().__init__(token)
        self.name = name
        self.params = params
        self.body = body
        self.return_type = return_type

class Parameter(ASTNode):
    """Corresponde a parte de ParamsForm na EBNF: Tipo Ident"""
    def __init__(self, token: Token, name: Token, param_type: str):
        super().__init__(token)
        self.name = name
        self.param_type = param_type

# --- Comandos (Statements) ---

class Block(Statement):
    """Corresponde a Bloco na EBNF: "{" SeqComando "}" """
    def __init__(self, token: Token, statements: List[Statement]):
        super().__init__(token)
        self.statements = statements

class ExprStmt(Statement):
    """Comando de expressão: uma expressão seguida por ';' """
    def __init__(self, token: Token, expression: Expression):
        super().__init__(token)
        self.expression = expression

class PrintStmt(Statement):
    """Corresponde a ComandoPrint na EBNF: "print" "(" Expressao [ "," Numero ] ")" ";" """
    def __init__(self, token: Token, expression: Expression, width: Optional[Expression] = None):
        super().__init__(token)
        self.expression = expression
        self.width = width

class IfStmt(Statement):
    """Corresponde a ComandoIf na EBNF: "if" "(" Condicao ")" Comando [ "else" Comando ] """
    def __init__(self, token: Token, condition: Expression, then_branch: Statement, else_branch: Optional[Statement]):
        super().__init__(token)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileStmt(Statement):
    """Corresponde a ComandoWhile na EBNF: "while" "(" Condicao ")" Comando """
    def __init__(self, token: Token, condition: Expression, body: Statement):
        super().__init__(token)
        self.condition = condition
        self.body = body

class ReturnStmt(Statement):
    """Corresponde a ComandoReturn na EBNF: "return" [ Expressao ] ";" """
    def __init__(self, token: Token, value: Optional[Expression]):
        super().__init__(token)
        self.value = value