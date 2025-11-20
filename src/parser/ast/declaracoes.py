from typing import List, Optional
from .ast_base import ASTNode
from ...lexer.tokens import Token # Importa Token para referência de tipo

# --- Declarações ---
class VarDecl(ASTNode):
    """Corresponde a DeclVar na EBNF: var Tipo Ident { "," Ident } ";" """
    def __init__(self, token: Token, identifier: Token, var_type: str, initial_value: Optional[ASTNode], is_mutable: bool = True):
        super().__init__(token)
        self.identifier = identifier
        self.var_type = var_type
        self.initial_value = initial_value
        self.is_mutable = is_mutable

class FunctionDecl(ASTNode):
    """Corresponde a DeclMetodo na EBNF: void Ident "(" ParamsFormOpt ")" ... Bloco"""
    def __init__(self, token: Token, name: Token, params: List['Parameter'], body: 'ASTNode', return_type: str = 'void'):
        super().__init__(token)
        self.name = name
        self.params = params
        self.body = body
        self.return_type = return_type

# O Parameter já usava ASTNode, mas agora ela está importada corretamente
class Parameter(ASTNode):
    """Corresponde a parte de ParamsForm na EBNF: Tipo Ident"""
    def __init__(self, token: Token, name: Token, param_type: str):
        super().__init__(token)
        self.name = name
        self.param_type = param_type

# --- Comandos (Statements) ---

class Block(ASTNode):
    """Corresponde a Bloco na EBNF: "{" SeqComando "}" """
    def __init__(self, token: Token, statements: List[ASTNode]):
        super().__init__(token)
        self.statements = statements

class ExprStmt(ASTNode):
    """Comando de expressão: uma expressão seguida por ';' """
    def __init__(self, token: Token, expression: ASTNode):
        super().__init__(token)
        self.expression = expression

class PrintStmt(ASTNode):
    """Corresponde a ComandoPrint na EBNF: "print" "(" Expressao [ "," Numero ] ")" ";" """
    def __init__(self, token: Token, expression: ASTNode, width: Optional[ASTNode] = None):
        super().__init__(token)
        self.expression = expression
        self.width = width

class IfStmt(ASTNode):
    """Corresponde a ComandoIf na EBNF: "if" "(" Condicao ")" Comando [ "else" Comando ] """
    def __init__(self, token: Token, condition: ASTNode, then_branch: ASTNode, else_branch: Optional[ASTNode]):
        super().__init__(token)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileStmt(ASTNode):
    """Corresponde a ComandoWhile na EBNF: "while" "(" Condicao ")" Comando """
    def __init__(self, token: Token, condition: ASTNode, body: ASTNode):
        super().__init__(token)
        self.condition = condition
        self.body = body

class ReturnStmt(ASTNode):
    """Corresponde a ComandoReturn na EBNF: "return" [ Expressao ] ";" """
    def __init__(self, token: Token, value: Optional[ASTNode]):
        super().__init__(token)
        self.value = value