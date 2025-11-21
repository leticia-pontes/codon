from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple
from ...lexer.tokens import Token
import sys

@dataclass
class ASTNode:
    token: Token
    # Propriedades para o analyzer pegar linha/coluna
    @property
    def line(self): return self.token.line
    @property
    def col(self): return self.token.col

@dataclass
class Programa(ASTNode):
    declaracoes: List[Any] = field(default_factory=list)

# --- Declarações ---
@dataclass
class DeclaracaoFuncao(ASTNode):
    nome: str
    parametros: List[str] # Analyzer espera lista de strings "nome: tipo"
    corpo: List[Any]      # Analyzer espera lista de statements
    tipo_retorno: str = 'void'
    is_procedure: bool = False

@dataclass
class DeclaracaoClasse(ASTNode):
    nome: str
    campos: List[Tuple[str, str]] # [(nome, tipo)]

@dataclass
class DeclaracaoVariavel(ASTNode):
    # Helper não usado diretamente pelo analyzer, mas útil
    nome: str
    tipo: str
    valor: Optional[Any] = None

# --- Expressões ---
@dataclass
class Expressao(ASTNode):
    pass

@dataclass
class Literal(Expressao):
    valor: Any

@dataclass
class Variavel(Expressao): # Analyzer usa 'Variavel' para identificadores
    nome: str

@dataclass
class ExpressaoBinaria(Expressao):
    esquerda: Any
    operador: str
    direita: Any

@dataclass
class ExpressaoUnaria(Expressao):
    operador: str
    direita: Any

@dataclass
class ChamadaFuncao(Expressao):
    nome: Any # Pode ser Variavel ou Expressao
    argumentos: List[Any] = field(default_factory=list)

@dataclass
class AcessoArray(Expressao):
    alvo: Any
    indice: Any

@dataclass
class AcessoCampo(Expressao):
    alvo: Any
    campo: str

@dataclass
class CriacaoClasse(Expressao):
    nome: str
    argumentos: List[Any] = field(default_factory=list)

@dataclass
class CriacaoArray(Expressao):
    tipo: str
    tamanho: Any

# --- Instruções ---
@dataclass
class InstrucaoAtribuicao(ASTNode):
    alvo: Any
    valor: Any

@dataclass
class InstrucaoIf(ASTNode):
    condicao: Any
    bloco_if: List[Any]
    elif_blocos: List[Tuple[Any, List[Any]]] = field(default_factory=list)
    bloco_else: List[Any] = field(default_factory=list)

@dataclass
class InstrucaoLoopWhile(ASTNode):
    condicao: Any
    corpo: List[Any]

@dataclass
class InstrucaoLoopFor(ASTNode):
    inicializacao: Any
    condicao: Any
    passo: Any
    corpo: List[Any]

@dataclass
class InstrucaoImpressao(ASTNode):
    expressao: Any

@dataclass
class InstrucaoRetorno(ASTNode):
    expressao: Optional[Any] = None

@dataclass
class InstrucaoExpressao(ASTNode):
    expressao: Any

# --- ALIASES PARA O PARSER IMPORTAR ---
# O Parser vai tentar usar nomes antigos ou ingles, mapeamos aqui
Program = Programa
VariableDeclaration = DeclaracaoVariavel
FunctionDeclaration = DeclaracaoFuncao
ClassDeclaration = DeclaracaoClasse
Identifier = Variavel
LiteralExpr = Literal
BinaryExpression = ExpressaoBinaria
UnaryExpression = ExpressaoUnaria
CallExpression = ChamadaFuncao
IndexExpression = AcessoArray
MemberAccessExpression = AcessoCampo
AssignmentExpression = InstrucaoAtribuicao # Parser trata atribuição como expressão as vezes
Statement = ASTNode
Expression = Expressao
Block = list # Parser usa Block, mas analyzer usa list. Vamos adaptar no parser.

__all__ = [
    "ASTNode", "Programa", "DeclaracaoFuncao", "DeclaracaoClasse", "DeclaracaoVariavel",
    "Expressao", "Literal", "Variavel", "ExpressaoBinaria", "ExpressaoUnaria",
    "ChamadaFuncao", "AcessoArray", "AcessoCampo", "CriacaoClasse", "CriacaoArray",
    "InstrucaoAtribuicao", "InstrucaoIf", "InstrucaoLoopWhile", "InstrucaoLoopFor",
    "InstrucaoImpressao", "InstrucaoRetorno", "InstrucaoExpressao",
    # Aliases
    "Program", "VariableDeclaration", "FunctionDeclaration", "Identifier", "BinaryExpression",
    "UnaryExpression", "CallExpression", "IndexExpression", "MemberAccessExpression", "AssignmentExpression"
]