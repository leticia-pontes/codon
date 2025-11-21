from typing import Dict, List, Optional, Tuple, Union
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, DeclaracaoClasse, InstrucaoAtribuicao,
    InstrucaoIf, InstrucaoLoopWhile, InstrucaoLoopFor, InstrucaoImpressao,
    InstrucaoRetorno, ExpressaoBinaria, ExpressaoUnaria, Literal, Variavel,
    ChamadaFuncao, AcessoArray, AcessoCampo, CriacaoClasse, CriacaoArray,
    ASTNode
)
from src.utils.erros import ErrorHandler, SemanticError
from .tabela_simbolos import Symbol, SymbolTable

# --- Utilitários de Tipo e Helpers ---

# Função para inferir o tipo de um Literal (simples, pois não temos a AST completa)
def _infer_literal_type(value) -> str:
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, str):
        # Assumindo que strings simples são 'string'
        return 'string'
    return 'unknown_type'

# Função para determinar o tipo resultante de uma operação binária
def _get_binary_result_type(op: str, left_type: str, right_type: str) -> Optional[str]:
    # Operadores Aritméticos e de Comparação
    numeric_ops = {'+', '-', '*', '/', '%', '==', '!=', '>', '<', '>=', '<='}

    # Lógica de tipos para operadores numéricos
    if op in numeric_ops:
        if left_type in {'int', 'float'} and right_type in {'int', 'float'}:
            # Se for comparação, o resultado é 'bool'
            if op in {'==', '!=', '>', '<', '>=', '<='}:
                return 'bool'
            # Promoção de tipo: se houver float, o resultado é 'float', senão é 'int'
            return 'float' if 'float' in {left_type, right_type} else 'int'

    # Lógica de tipo para operadores de Concatenação (ex: string + string)
    if op == '+':
        if left_type == 'string' and right_type == 'string':
            return 'string'

    # Lógica de tipo para operadores booleanos
    if op in {'&&', '||'}:
        if left_type == 'bool' and right_type == 'bool':
            return 'bool'

    # TODO: Adicionar lógica para operadores biológicos
    if op == '->':
        if left_type == 'dna' and right_type == 'rna':
            return 'rna'

    return None # Tipos incompatíveis

class SemanticAnalyzer:
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        self.error_handler = error_handler or ErrorHandler()

        self.global_scope = SymbolTable(scope_name="global")
        self.current_scope = self.global_scope

        self.current_function: Optional[Symbol] = None
        self.found_return_in_current_function: bool = False

        self.primitive_types = {"int", "float", "bool", "string", "dna", "rna", "prot", "void"}
        self._initialize_global_scope()

    def _initialize_global_scope(self):
        for t_name in self.primitive_types:
            self.global_scope.define(Symbol(t_name, t_name, 'type'), self.error_handler)

    def _get_coords(self, node: ASTNode) -> Tuple[int, int]:
        """Tenta extrair linha/coluna do nó da AST."""
        return getattr(node, 'line', -1), getattr(node, 'col', -1)

    def push_scope(self, name: str = "local"):
        self.current_scope = self.current_scope.enter_scope(name)

    def pop_scope(self):
        self.current_scope = self.current_scope.exit_scope()

    def analyze(self, program: Programa):
        # ... (Passos de registro e análise) ...
        for decl in program.declaracoes:
            if isinstance(decl, DeclaracaoFuncao):
                self._register_function(decl)
            elif isinstance(decl, DeclaracaoClasse):
                self._register_class(decl)

        for decl in program.declaracoes:
            self._analyze_declaration(decl)

        if not self.error_handler.has_errors():
            print("\nAnalise Semantica concluida sem erros. [OK]")
        else:
            print(f"\nAnálise Semântica concluída com {len(self.error_handler.errors)} erros. ❌")


    def _register_function(self, decl: DeclaracaoFuncao):
        line, col = self._get_coords(decl)
        param_count = len(decl.parametros) if decl.parametros else 0

        ret_type = 'void' if decl.is_procedure else getattr(decl, 'tipo_retorno', 'unknown_type')

        func_symbol = Symbol(
            decl.nome,
            ret_type,
            'function',
            line, col,
            param_count=param_count,
            is_procedure=decl.is_procedure
        )
        self.current_scope.define(func_symbol, self.error_handler)

    def _register_class(self, decl: DeclaracaoClasse):
        # ... (Lógica de registro da classe e checagem de SEM025) ...
        line, col = self._get_coords(decl)

        fields = {}
        field_names = set()

        for fname, ftype in decl.campos:
            if fname in field_names:
                self.error_handler.report_error(SemanticError(
                    f"Campo duplicado '{fname}' na classe '{decl.nome}'.", line, col, "SEM025"))
            field_names.add(fname)
            fields[fname] = ftype

        class_symbol = Symbol(
            decl.nome,
            decl.nome,
            'class',
            line, col,
            fields=fields
        )
        self.current_scope.define(class_symbol, self.error_handler)

    def _analyze_declaration(self, decl: ASTNode):
        if isinstance(decl, DeclaracaoFuncao):
            self._analyze_function(decl)
        elif isinstance(decl, DeclaracaoClasse):
            self._analyze_class(decl)
        else:
            self._analyze_stmt(decl)

    def _analyze_class(self, decl: DeclaracaoClasse):
        self.push_scope(f"class_{decl.nome}")
        for _, field_type in decl.campos:
            if self.global_scope.lookup(field_type) is None:
                 line, col = self._get_coords(decl)
                 self.error_handler.report_error(SemanticError(
                     f"Tipo '{field_type}' do campo é indefinido.", line, col, "SEM???"
                 )) # SEM027, talvez
        self.pop_scope()

    def _analyze_function(self, decl: DeclaracaoFuncao):
        self.current_function = self.current_scope.lookup(decl.nome)
        self.found_return_in_current_function = False

        self.push_scope(f"func_{decl.nome}")

        if decl.parametros:
            for p_raw in decl.parametros:
                param_parts = p_raw.split(':', 1)
                param_name = param_parts[0].strip()
                # Tenta inferir o tipo do parâmetro (exigindo ': tipo' na AST)
                param_type = param_parts[1].strip() if len(param_parts) > 1 else 'unknown_type'

                line, col = self._get_coords(decl)

                param_symbol = Symbol(param_name, param_type, 'param', line, col)
                self.current_scope.define(param_symbol, self.error_handler)

        for stmt in decl.corpo:
            self._analyze_stmt(stmt)

        if not self.current_function.is_procedure and not self.found_return_in_current_function:
            line, col = self._get_coords(decl)
            self.error_handler.report_error(SemanticError(
                f"Função '{decl.nome}' (não-procedure) requer uma instrução 'return'.", line, col, "SEM008"
            ))

        self.pop_scope()
        self.current_function = None


    # --- Statements ---
    def _analyze_stmt(self, node: ASTNode):
        if isinstance(node, InstrucaoAtribuicao):
            self._analyze_assignment(node)
        elif isinstance(node, InstrucaoIf):
            self._analyze_if(node)
        elif isinstance(node, InstrucaoLoopWhile):
            self._analyze_while(node)
        elif isinstance(node, InstrucaoLoopFor):
            self._analyze_for(node)
        elif isinstance(node, InstrucaoImpressao):
            self._analyze_expr(node.expressao)
        elif isinstance(node, InstrucaoRetorno):
            line, col = self._get_coords(node)
            if self.current_function is None:
                self.error_handler.report_error(SemanticError(
                    "Instrução 'return' fora de uma função.", line, col, "SEM006"
                ))
                return # Impede análise de retorno inválido

            returned_type = 'void'
            if node.expressao:
                returned_type = self._analyze_expr(node.expressao)

            expected_type = self.current_function.type

            if self.current_function.is_procedure:
                if returned_type != 'void':
                     self.error_handler.report_error(SemanticError(
                        f"Uma procedure não pode retornar um valor de tipo '{returned_type}'.", line, col, "SEM013"
                    ))
            elif returned_type != expected_type:
                # Simplificado: se os tipos não coincidirem, é erro.
                self.error_handler.report_error(SemanticError(
                    f"O tipo de retorno da função '{self.current_function.name}' é incompatível. Esperado '{expected_type}', Recebido '{returned_type}'.", line, col, "SEM012"
                ))

            self.found_return_in_current_function = True
        else:
            if node is not None:
                self._analyze_expr(node)

    def _analyze_assignment(self, node: InstrucaoAtribuicao):
        # 1. Analisa e infere o tipo do lado direito (RHS)
        rhs_type = self._analyze_expr(node.valor)

        # 2. Analisa o lado esquerdo (LHS)
        alvo = node.alvo
        line, col = self._get_coords(alvo)

        if isinstance(alvo, Variavel):
            var_symbol = self.current_scope.lookup(alvo.nome)

            if var_symbol is None:
                # Declaração implícita: assume o tipo do RHS
                self.current_scope.define(Symbol(alvo.nome, rhs_type, 'var', line, col), self.error_handler)
            else:
                if var_symbol.kind == 'const':
                    self.error_handler.report_error(SemanticError(...))

                # TODO: Checagem de compatibilidade de tipo (SEM015)
                # if var_symbol.type != rhs_type and var_symbol.type != 'unknown_type':
                #     self.error_handler.report_error(SemanticError(...))

                # Se for unknown, assume o tipo do RHS
                if var_symbol.type == 'unknown_type':
                    var_symbol.type = rhs_type

        elif isinstance(alvo, (AcessoCampo, AcessoArray)):
            # Analisa as partes do acesso (retorna o tipo do campo/elemento acessado)
            # TODO: Aqui é necessário retornar o tipo do acesso para verificar compatibilidade com RHS
            self._analyze_expr(alvo)


    def _analyze_if(self, node: InstrucaoIf):
        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        if cond_type != 'bool':
            self.error_handler.report_error(SemanticError(
                "A condição da instrução 'if' deve ser do tipo 'bool'.", line, col, "SEM018"
            ))

        self.push_scope("if_block")
        for s in node.bloco_if:
            self._analyze_stmt(s)
        self.pop_scope()

        for (cond, bloco) in node.elif_blocos:
            elif_cond_type = self._analyze_expr(cond)
            line, col = self._get_coords(cond)
            if elif_cond_type != 'bool':
                self.error_handler.report_error(SemanticError(
                    "A condição da instrução 'elif' deve ser do tipo 'bool'.", line, col, "SEM018"
                ))

            self.push_scope("elif_block")
            for s in bloco:
                self._analyze_stmt(s)
            self.pop_scope()

        if node.bloco_else:
            self.push_scope("else_block")
            for s in node.bloco_else:
                self._analyze_stmt(s)
            self.pop_scope()

    def _analyze_while(self, node: InstrucaoLoopWhile):
        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        if cond_type != 'bool':
            self.error_handler.report_error(SemanticError(
                "A condição do loop 'while' deve ser do tipo 'bool'.", line, col, "SEM018"
            ))

        self.push_scope("while_body")
        for s in node.corpo:
            self._analyze_stmt(s)
        self.pop_scope()

    def _analyze_for(self, node: InstrucaoLoopFor):
        self.push_scope("for_loop")
        self._analyze_stmt(node.inicializacao)

        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        if cond_type != 'bool':
            self.error_handler.report_error(SemanticError(
                "A condição do loop 'for' deve ser do tipo 'bool'.", line, col, "SEM018"
            ))

        self._analyze_stmt(node.passo)
        for s in node.corpo:
            self._analyze_stmt(s)
        self.pop_scope()


    # --- Expressions ---
    def _analyze_expr(self, expr: ASTNode) -> str:
        if expr is None:
            return 'void'

        line, col = self._get_coords(expr)

        if isinstance(expr, Literal):
            # Retorna o tipo inferido do literal
            return _infer_literal_type(expr.valor)

        if isinstance(expr, Variavel):
            var_symbol = self.current_scope.lookup(expr.nome)
            if var_symbol is None:
                self.error_handler.report_error(SemanticError(
                    f"Uso de variável não definida: '{expr.nome}'", line, col, "SEM003"))
                return 'unknown_type'
            return var_symbol.type

        elif isinstance(expr, ExpressaoBinaria):
            left_type = self._analyze_expr(expr.esquerda)
            right_type = self._analyze_expr(expr.direita)

            result_type = _get_binary_result_type(expr.operador, left_type, right_type)

            if result_type is None:
                # SEM010: Tipos incompatíveis para operação (ou operando inválido)
                self.error_handler.report_error(SemanticError(
                    f"Tipos incompatíveis '{left_type}' e '{right_type}' para o operador binário '{expr.operador}'.", line, col, "SEM010"))
                return 'unknown_type'

            return result_type

        elif isinstance(expr, ExpressaoUnaria):
            right_type = self._analyze_expr(expr.direita)

            if expr.operador in {'+', '-'}: # Negação numérica
                if right_type not in {'int', 'float'}:
                    self.error_handler.report_error(SemanticError(
                        f"Operador unário '{expr.operador}' requer tipo numérico, recebeu '{right_type}'.", line, col, "SEM011"))
                    return 'unknown_type'
                return right_type

            elif expr.operador == '!': # Negação booleana
                if right_type != 'bool':
                    self.error_handler.report_error(SemanticError(
                        f"Operador unário '{expr.operador}' requer tipo 'bool', recebeu '{right_type}'.", line, col, "SEM011"))
                    return 'unknown_type'
                return 'bool'

            return 'unknown_type'

        elif isinstance(expr, ChamadaFuncao):
            fn_name_node = expr.nome
            func_symbol = None
            fn_name = ""

            if isinstance(fn_name_node, Variavel):
                fn_name = fn_name_node.nome
                func_symbol = self.current_scope.lookup(fn_name)

                if func_symbol is None or func_symbol.kind != 'function':
                    self.error_handler.report_error(SemanticError(
                        f"Chamada para função não definida: '{fn_name}'", line, col, "SEM005"))
                else:
                    expected = func_symbol.param_count
                    got = len(expr.argumentos) if expr.argumentos else 0
                    if expected != got:
                        self.error_handler.report_error(SemanticError(
                            f"Função '{fn_name}' espera {expected} args mas recebeu {got}", line, col, "SEM009"))
            else:
                self._analyze_expr(fn_name_node)

            for a in expr.argumentos:
                self._analyze_expr(a)

            # Retorna o tipo de retorno da função (se encontrada)
            return func_symbol.type if func_symbol else 'unknown_type'

        elif isinstance(expr, (AcessoArray, AcessoCampo)):
            self._analyze_expr(expr.alvo)
            if isinstance(expr, AcessoArray):
                index_type = self._analyze_expr(expr.indice)
                if index_type != 'int':
                    self.error_handler.report_error(SemanticError(
                        f"O índice do array deve ser do tipo 'int', recebeu '{index_type}'.", line, col, "SEM017"
                    ))
                return 'unknown_type' # Retorna o tipo do elemento (desconhecido por enquanto)

            return 'unknown_type'

        elif isinstance(expr, (CriacaoClasse, CriacaoArray)):
            for a in (expr.argumentos if isinstance(expr, CriacaoClasse) else [expr.tamanho]):
                self._analyze_expr(a)
            # Retorna o nome da classe ou array
            return expr.nome if isinstance(expr, CriacaoClasse) else 'Array<unknown>'

        # Caso de fallback
        return 'unknown_type'