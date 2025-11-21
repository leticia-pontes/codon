from typing import Optional, Dict, List
from src.utils.erros import ErrorHandler, SemanticError

class Symbol:
    """Representa um símbolo (variável, função, etc.) na Tabela de Símbolos."""
    def __init__(self, name: str, type_name: str, kind: str, line: int = -1, column: int = -1, **kwargs):
        self.name = name
        self.type_name = type_name
        self.kind = kind
        self.line = line
        self.column = column

        for key, value in kwargs.items():
            setattr(self, key, value)

class SymbolTable:
    """Gerencia a Tabela de Símbolos e escopos aninhados."""
    def __init__(self, parent: Optional['SymbolTable'] = None, scope_name: str = "global"):
        self.parent = parent
        self.scope_name = scope_name
        self.symbols: Dict[str, Symbol] = {} # name -> Symbol
        self.children: List['SymbolTable'] = [] # Child SymbolTable objects

    def define(self, symbol: Symbol, error_handler: ErrorHandler):
        """Define um novo símbolo no escopo atual, verificando redeclaração."""
        if symbol.name in self.symbols:
            error_handler.report_error(SemanticError(
                f"Símbolo '{symbol.name}' já foi declarado neste escopo.",
                symbol.line, symbol.column, "SEM001" # Usando um código de erro sugerido
            ))
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Optional[Symbol]:
        """Procura um símbolo, começando no escopo atual e subindo para os pais."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def enter_scope(self, scope_name: str = "local") -> 'SymbolTable':
        """Cria e entra em um novo escopo aninhado."""
        new_scope = SymbolTable(parent=self, scope_name=scope_name)
        # O novo escopo se torna filho do escopo atual, mas o Analisador Semântico
        # é responsável por atualizar o 'current_scope'
        self.children.append(new_scope)
        return new_scope

    def exit_scope(self) -> 'SymbolTable':
        """Retorna ao escopo pai."""
        if self.parent is None:
            raise Exception("Não é possível sair do escopo global.")
        return self.parent