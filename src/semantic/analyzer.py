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


def _infer_literal_type(value) -> str:
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, str):
        return 'char' if len(value) == 1 else 'string'
    return 'unknown_type'


def _get_binary_result_type(op: str, left_type: str, right_type: str) -> Optional[str]:
    arithmetic_ops = {'+', '-', '*', '/', '%'}
    comparison_ops = {'==', '!=', '>', '<', '>=', '<='}
    logical_ops = {'&&', '||'}

    numeric = {'int', 'float', 'decimal'}

    if op in arithmetic_ops:
        if left_type in numeric and right_type in numeric:
            if 'decimal' in {left_type, right_type}:
                return 'decimal'
            if 'float' in {left_type, right_type}:
                return 'float'
            return 'int'
        if op == '+' and left_type == 'string' and right_type == 'string':
            return 'string'
        return None

    if op in comparison_ops:
        numeric = {'int', 'float', 'decimal'}
        if (left_type in numeric and right_type in numeric) or \
           (left_type == right_type == 'string'):
            return 'bool'
        return None

    if op in logical_ops:
        if left_type == 'bool' and right_type == 'bool':
            return 'bool'
        return None

    if op == '->':
        if left_type == 'dna' and right_type == 'rna':
            return 'rna'

    return None


class SemanticAnalyzer:
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        self.error_handler = error_handler or ErrorHandler()

        self.global_scope = SymbolTable(scope_name="global")
        self.current_scope = self.global_scope

        self.current_function: Optional[Symbol] = None
        self.found_return_in_current_function: bool = False

        self.primitive_types = {
            "int", "float", "decimal", "bool", "char", "string",
            "dna", "rna", "prot", "Nbase", "void"
        }

        self._initialize_global_scope()

    def _initialize_global_scope(self):
        for t_name in self.primitive_types:
            self.global_scope.define(Symbol(t_name, t_name, 'type'), self.error_handler)
        self.global_scope.define(Symbol('length', 'int', 'function', param_count=1), self.error_handler)

    def _get_coords(self, node: ASTNode) -> Tuple[int, int]:
        return getattr(node, 'line', -1), getattr(node, 'col', -1)

    def push_scope(self, name: str = "local"):
        self.current_scope = self.current_scope.enter_scope(name)

    def pop_scope(self):
        self.current_scope = self.current_scope.exit_scope()

    def analyze(self, program: Programa):
        for decl in program.declaracoes:
            if isinstance(decl, DeclaracaoFuncao):
                self._register_function(decl)
            elif isinstance(decl, DeclaracaoClasse):
                self._register_class(decl)

        for decl in program.declaracoes:
            self._analyze_declaration(decl)

        # if not self.error_handler.has_errors():
        #     print("\nAnalise Semantica concluida sem erros.\n")
        # else:
        #     print(f"Analise Semantica concluida com {len(self.error_handler.errors)} erros.\n")

    def _register_function(self, decl: DeclaracaoFuncao):
        line, col = self._get_coords(decl)
        param_count = len(decl.parametros) if decl.parametros else 0

        ret_type = getattr(decl, 'tipo_retorno', 'unknown_type')
        if decl.is_procedure:
            ret_type = 'void'

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
        line, col = self._get_coords(decl)

        fields = {}
        field_names = set()

        for fname, ftype in decl.campos:
            if fname in field_names:
                self.error_handler.report_error(SemanticError(
                    f"Campo duplicado '{fname}' na classe '{decl.nome}'.",
                    line, col, "SEM025"))
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
        elif decl is not None:
            self._analyze_stmt(decl)

    def _analyze_class(self, decl: DeclaracaoClasse):
        for _, field_type in decl.campos:
            if self.global_scope.lookup(field_type) is None:
                line, col = self._get_coords(decl)
                self.error_handler.report_error(SemanticError(
                    f"Tipo '{field_type}' do campo é indefinido (classe ou primitivo).",
                    line, col, "SEM027"
                ))

    def _analyze_function(self, decl: DeclaracaoFuncao):
        self.current_function = self.current_scope.lookup(decl.nome)
        self.found_return_in_current_function = False

        self.push_scope(f"func_{decl.nome}")

        if decl.parametros:
            for param_name, param_type in decl.parametros:
                line, col = self._get_coords(decl)
                if self.global_scope.lookup(param_type) is None:
                    self.error_handler.report_error(SemanticError(
                        f"Tipo '{param_type}' do parâmetro '{param_name}' é indefinido.",
                        line, col, "SEM027"
                    ))

                param_symbol = Symbol(param_name, param_type, 'param', line, col)
                self.current_scope.define(param_symbol, self.error_handler)

        for stmt in decl.corpo:
            self._analyze_stmt(stmt)

        if (not self.current_function.is_procedure) and \
           (self.current_function.type != 'void') and \
           (not self.found_return_in_current_function):
            line, col = self._get_coords(decl)
            self.error_handler.report_error(SemanticError(
                f"Função '{decl.nome}' (não-procedure) requer uma instrução 'return'.",
                line, col, "SEM008"
            ))

        self.pop_scope()
        self.current_function = None

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
            self._analyze_return(node)
        elif isinstance(node, (Variavel, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria,
                               Literal, AcessoArray, AcessoCampo)):
            self._analyze_expr(node)

    def _expand_compound_assignment(self, node: InstrucaoAtribuicao):
        op = node.operador
        if op == "=":
            return node.valor

        if op in ["+=", "-=", "*=", "/=", "%="]:
            base_op = op[0]
            return ExpressaoBinaria(node.alvo, base_op, node.valor,
                                    line=node.line, col=node.col)

        return node.valor

    def _analyze_return(self, node: InstrucaoRetorno):
        line, col = self._get_coords(node)

        if self.current_function is None:
            self.error_handler.report_error(SemanticError(
                "Instrução 'return' fora de uma função.",
                line, col, "SEM006"))
            return

        returned_type = 'void'
        if node.expressao:
            returned_type = self._analyze_expr(node.expressao)

        expected_type = self.current_function.type

        if self.current_function.is_procedure:
            if returned_type != 'void':
                self.error_handler.report_error(SemanticError(
                    f"Uma procedure não pode retornar um valor de tipo '{returned_type}'.",
                    line, col, "SEM013"))
        elif returned_type != expected_type:
            if not (expected_type == 'float' and returned_type == 'int'):
                self.error_handler.report_error(SemanticError(
                    f"O tipo de retorno da função '{self.current_function.name}' é incompatível. "
                    f"Esperado '{expected_type}', Recebido '{returned_type}'.",
                    line, col, "SEM012"))

        self.found_return_in_current_function = True

    def _analyze_assignment(self, node: InstrucaoAtribuicao):
        expanded_value = self._expand_compound_assignment(node)
        rhs_type = self._analyze_expr(expanded_value)

        alvo = node.alvo
        line, col = self._get_coords(alvo)

        if isinstance(alvo, Variavel):
            var_symbol = self.current_scope.lookup(alvo.nome)

            if var_symbol is None:
                self.current_scope.define(Symbol(
                    alvo.nome, rhs_type, 'var', line, col
                ), self.error_handler)
                return

            if var_symbol.kind == 'const':
                self.error_handler.report_error(SemanticError(
                    f"Variável '{alvo.nome}' é const e não pode ser atribuída.",
                    line, col, "SEM014"))
                return

            expected_type = var_symbol.type
            if expected_type != 'unknown_type' and rhs_type != 'unknown_type':
                if expected_type != rhs_type:
                    numeric = {'int', 'float', 'decimal'}
                    if expected_type in numeric and rhs_type in numeric:
                        return
                    if expected_type == 'Nbase' and rhs_type == 'char':
                        return
                    self.error_handler.report_error(SemanticError(
                        f"Tipo incompatível na atribuição: '{expected_type}' := '{rhs_type}'",
                        line, col, "SEM015"))

        elif isinstance(alvo, (AcessoCampo, AcessoArray)):
            alvo_type = self._analyze_expr(alvo)
            if alvo_type != 'unknown_type' and alvo_type is not None:
                expected = alvo_type
                if expected != rhs_type:
                    numeric = {'int', 'float', 'decimal'}
                    if expected in numeric and rhs_type in numeric:
                        return
                    if expected == 'Nbase' and rhs_type == 'char':
                        return
                    self.error_handler.report_error(SemanticError(
                        f"Tipo incompatível na atribuição por acesso: '{expected}' := '{rhs_type}'",
                        line, col, "SEM015"))

    def _analyze_if(self, node: InstrucaoIf):
        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        if cond_type != 'bool':
            self.error_handler.report_error(SemanticError(
                "A condição da instrução 'if' deve ser do tipo 'bool'.",
                line, col, "SEM018"))

        self.push_scope("if_block")
        for s in node.bloco_if:
            self._analyze_stmt(s)
        self.pop_scope()

        for (cond, bloco) in node.elif_blocos:
            elif_cond_type = self._analyze_expr(cond)
            line, col = self._get_coords(cond)
            if elif_cond_type != 'bool':
                self.error_handler.report_error(SemanticError(
                    "A condição da instrução 'elif' deve ser do tipo 'bool'.",
                    line, col, "SEM018"))

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
                "A condição do loop 'while' deve ser do tipo 'bool'.",
                line, col, "SEM018"))

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
                "A condição do loop 'for' deve ser do tipo 'bool'.",
                line, col, "SEM018"))

        self._analyze_stmt(node.passo)
        for s in node.corpo:
            self._analyze_stmt(s)

        self.pop_scope()

    def _analyze_expr(self, expr: ASTNode) -> str:
        if expr is None:
            return 'void'

        line, col = self._get_coords(expr)

        if isinstance(expr, Literal):
            return _infer_literal_type(expr.valor)

        if isinstance(expr, Variavel):
            var_symbol = self.current_scope.lookup(expr.nome)
            if var_symbol is None:
                self.error_handler.report_error(SemanticError(
                    f"Uso de variável não definida: '{expr.nome}'",
                    line, col, "SEM003"))
                return 'unknown_type'
            return var_symbol.type

        if isinstance(expr, ExpressaoBinaria):
            left_type = self._analyze_expr(expr.esquerda)
            right_type = self._analyze_expr(expr.direita)

            result_type = _get_binary_result_type(expr.operador, left_type, right_type)

            if result_type is None:
                self.error_handler.report_error(SemanticError(
                    f"Tipos incompatíveis '{left_type}' e '{right_type}' para o operador binário '{expr.operador}'.",
                    line, col, "SEM010"))
                return 'unknown_type'

            return result_type

        if isinstance(expr, ExpressaoUnaria):
            right_type = self._analyze_expr(expr.direita)

            if expr.operador in {'+', '-'}:
                if right_type not in {'int', 'float'}:
                    self.error_handler.report_error(SemanticError(
                        f"Operador unário '{expr.operador}' requer tipo numérico, recebeu '{right_type}'.",
                        line, col, "SEM011"))
                    return 'unknown_type'
                return right_type

            if expr.operador == '!':
                if right_type != 'bool':
                    self.error_handler.report_error(SemanticError(
                        f"Operador unário '{expr.operador}' requer tipo 'bool', recebeu '{right_type}'.",
                        line, col, "SEM011"))
                    return 'unknown_type'
                return 'bool'

            return 'unknown_type'

        if isinstance(expr, ChamadaFuncao):
            fn_name_node = expr.nome
            func_symbol = None
            fn_name = ""

            if isinstance(fn_name_node, Variavel):
                fn_name = fn_name_node.nome
                func_symbol = self.current_scope.lookup(fn_name)

                if func_symbol is None or func_symbol.kind != 'function':
                    class_symbol = self.current_scope.lookup(fn_name) or self.global_scope.lookup(fn_name)
                    if class_symbol and class_symbol.kind == 'class':
                        for a in expr.argumentos:
                            self._analyze_expr(a)
                        return class_symbol.type
                    self.error_handler.report_error(SemanticError(
                        f"Chamada para função não definida: '{fn_name}'",
                        line, col, "SEM005"))
                    func_symbol = None
                else:
                    expected = getattr(func_symbol, 'param_count', 0)
                    got = len(expr.argumentos) if expr.argumentos else 0
                    if expected != got:
                        self.error_handler.report_error(SemanticError(
                            f"Função '{fn_name}' espera {expected} args mas recebeu {got}",
                            line, col, "SEM009"))

            for a in expr.argumentos:
                self._analyze_expr(a)

            return func_symbol.type if func_symbol else 'unknown_type'

        if isinstance(expr, AcessoArray):
            alvo_type = self._analyze_expr(expr.alvo)
            index_type = self._analyze_expr(expr.indice)
            line, col = self._get_coords(expr)

            if index_type != 'int':
                self.error_handler.report_error(SemanticError(
                    f"O índice do array deve ser do tipo 'int', recebeu '{index_type}'.",
                    line, col, "SEM017"
                ))

            if not alvo_type.startswith('Array<'):
                self.error_handler.report_error(SemanticError(
                    f"Tentativa de indexar um tipo não-array: '{alvo_type}'.",
                    line, col, "SEM029"
                ))
                return 'unknown_type'

            return alvo_type[6:-1]

        if isinstance(expr, AcessoCampo):
            alvo_type = self._analyze_expr(expr.alvo)
            field_name = expr.campo
            line, col = self._get_coords(expr)

            class_symbol = self.global_scope.lookup(alvo_type)

            if class_symbol is None or class_symbol.kind != 'class':
                self.error_handler.report_error(SemanticError(
                    f"Acesso a campo ('{field_name}') de tipo inválido ou indefinido: '{alvo_type}'.",
                    line, col, "SEM026"))
                return 'unknown_type'

            class_fields = getattr(class_symbol, 'fields', {})
            if field_name not in class_fields:
                self.error_handler.report_error(SemanticError(
                    f"Campo '{field_name}' não existe na classe '{alvo_type}'.",
                    line, col, "SEM028"))
                return 'unknown_type'

            return class_fields[field_name]

        if isinstance(expr, CriacaoClasse):
            for a in expr.argumentos:
                self._analyze_expr(a)
            return expr.classe

        if isinstance(expr, CriacaoArray):
            size_type = self._analyze_expr(expr.tamanho)
            if size_type != 'int':
                self.error_handler.report_error(SemanticError(
                    f"O tamanho do array deve ser do tipo 'int', recebido '{size_type}'.",
                    line, col, "SEM030"
                ))
            return f'Array<{expr.tipo}>'

        return 'unknown_type'