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

def _infer_literal_type(value) -> str:
    """Função para inferir o tipo de um Literal (int, float, bool, string, char)."""
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, str):
        # Char literal vira string de tamanho 1; distinguir aqui
        return 'char' if len(value) == 1 else 'string'
    return 'unknown_type'

def _get_binary_result_type(op: str, left_type: str, right_type: str) -> Optional[str]:
    """Função para determinar o tipo resultante de uma operação binária (SEM010)."""
    arithmetic_ops = {'+', '-', '*', '/', '%'}
    comparison_ops = {'==', '!=', '>', '<', '>=', '<='}
    logical_ops = {'&&', '||'}

    numeric = {'int','float','decimal'}

    # 1. Operadores Aritméticos e Concatenção de String
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

    # 2. Operadores de Comparação
    if op in comparison_ops:
        numeric = {'int','float','decimal'}
        if (left_type in numeric and right_type in numeric) or \
           (left_type == right_type == 'string'):
            return 'bool'
        return None

    # 3. Operadores Lógicos
    if op in logical_ops:
        if left_type == 'bool' and right_type == 'bool':
            return 'bool'
        return None

    # 4. Operador Bio (exemplo)
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

        self.primitive_types = {"int", "float", "decimal", "bool", "char", "string", "dna", "rna", "prot", "Nbase", "void"}
        self._initialize_global_scope()

    def _initialize_global_scope(self):
        """Registra tipos primitivos e funções built-in no escopo global."""
        for t_name in self.primitive_types:
            self.global_scope.define(Symbol(t_name, t_name, 'type'), self.error_handler)
        # Built-ins mínimos
        self.global_scope.define(Symbol('length', 'int', 'function', param_count=1), self.error_handler)

    def _get_coords(self, node: ASTNode) -> Tuple[int, int]:
        """Tenta extrair linha/coluna do nó da AST."""
        return getattr(node, 'line', -1), getattr(node, 'col', -1)

    def push_scope(self, name: str = "local"):
        """Entra em um novo escopo."""
        self.current_scope = self.current_scope.enter_scope(name)

    def pop_scope(self):
        """Sai do escopo atual e volta ao pai."""
        self.current_scope = self.current_scope.exit_scope()

    def analyze(self, program: Programa):
        """Passo 1: Registro de funções e classes. Passo 2: Análise do corpo."""
        for decl in program.declaracoes:
            if isinstance(decl, DeclaracaoFuncao):
                self._register_function(decl)
            elif isinstance(decl, DeclaracaoClasse):
                self._register_class(decl)

        for decl in program.declaracoes:
            self._analyze_declaration(decl)

        if not self.error_handler.has_errors():
            print("\nAnalise Semantica concluida sem erros.\n")
        else:
            print(f"Analise Semantica concluida com {len(self.error_handler.errors)} erros.\n")

    # --- Registro ---
    def _register_function(self, decl: DeclaracaoFuncao):
        line, col = self._get_coords(decl)
        param_count = len(decl.parametros) if decl.parametros else 0

        # O tipo de retorno deve vir da AST (tipo_retorno) ou ser 'void' se for procedure.
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
                # SEM025: Campo duplicado na classe
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

    # --- Análise ---
    def _analyze_declaration(self, decl: ASTNode):
        if isinstance(decl, DeclaracaoFuncao):
            self._analyze_function(decl)
        elif isinstance(decl, DeclaracaoClasse):
            self._analyze_class(decl)
        elif decl is not None:
            # Para declarações que não são função/classe e estão no nível global
            self._analyze_stmt(decl)

    def _analyze_class(self, decl: DeclaracaoClasse):
        # Apenas checa se os tipos dos campos estão definidos (primitivo ou outra classe)
        for _, field_type in decl.campos:
            if self.global_scope.lookup(field_type) is None:
                line, col = self._get_coords(decl)
                self.error_handler.report_error(SemanticError(
                    f"Tipo '{field_type}' do campo é indefinido (classe ou primitivo).", line, col, "SEM027"
                ))

    def _analyze_function(self, decl: DeclaracaoFuncao):
        self.current_function = self.current_scope.lookup(decl.nome)
        self.found_return_in_current_function = False

        self.push_scope(f"func_{decl.nome}")

        # Correção da lógica de parâmetros para usar a estrutura (nome, tipo)
        if decl.parametros:
            for param_name, param_type in decl.parametros:
                line, col = self._get_coords(decl)

                # SEM027: Checagem do tipo do parâmetro
                if self.global_scope.lookup(param_type) is None:
                    self.error_handler.report_error(SemanticError(
                        f"Tipo '{param_type}' do parâmetro '{param_name}' é indefinido.", line, col, "SEM027"
                    ))

                param_symbol = Symbol(param_name, param_type, 'param', line, col)
                self.current_scope.define(param_symbol, self.error_handler)

        for stmt in decl.corpo:
            self._analyze_stmt(stmt)

        # SEM008: Função não-procedure sem return (exceção para retorno void)
        if (not self.current_function.is_procedure) and (self.current_function.type != 'void') and (not self.found_return_in_current_function):
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
            self._analyze_return(node)
        elif isinstance(node, (Variavel, ChamadaFuncao, ExpressaoBinaria, ExpressaoUnaria, Literal, AcessoArray, AcessoCampo)):
            # Permite expressões como statements (e.g., chamada de procedure)
            self._analyze_expr(node)

    def _analyze_return(self, node: InstrucaoRetorno):
        line, col = self._get_coords(node)

        if self.current_function is None:
            # SEM006: Return fora de função
            self.error_handler.report_error(SemanticError(
                "Instrução 'return' fora de uma função.", line, col, "SEM006"
            ))
            return

        returned_type = 'void'
        if node.expressao:
            returned_type = self._analyze_expr(node.expressao)

        expected_type = self.current_function.type

        if self.current_function.is_procedure:
            if returned_type != 'void':
                # SEM013: Procedure não pode retornar valor
                self.error_handler.report_error(SemanticError(
                    f"Uma procedure não pode retornar um valor de tipo '{returned_type}'.", line, col, "SEM013"
                ))
        elif returned_type != expected_type:
            # SEM012: Tipo de retorno incompatível (simplificado: sem conversão)
            # Permite a promoção int -> float
            if not (expected_type == 'float' and returned_type == 'int'):
                 self.error_handler.report_error(SemanticError(
                     f"O tipo de retorno da função '{self.current_function.name}' é incompatível. Esperado '{expected_type}', Recebido '{returned_type}'.", line, col, "SEM012"
                 ))

        self.found_return_in_current_function = True

    def _analyze_assignment(self, node: InstrucaoAtribuicao):
        # 1. Analisa e infere o tipo do lado direito (RHS)
        rhs_type = self._analyze_expr(node.valor)

        # 2. Analisa o lado esquerdo (LHS)
        alvo = node.alvo
        line, col = self._get_coords(alvo)

        if isinstance(alvo, Variavel):
            var_symbol = self.current_scope.lookup(alvo.nome)

            if var_symbol is None:
                # Declaração implícita: declara a variável no escopo atual
                self.current_scope.define(Symbol(alvo.nome, rhs_type, 'var', line, col), self.error_handler)
                return

            # Checagem de const
            if var_symbol.kind == 'const':
                self.error_handler.report_error(SemanticError(
                    f"Variável '{alvo.nome}' é const e não pode ser atribuída.", line, col, "SEM014"
                ))
                return

            # SEM015: Checagem de compatibilidade de tipo
            expected_type = var_symbol.type
            if expected_type != 'unknown_type' and rhs_type != 'unknown_type':
                if expected_type != rhs_type:
                    # Regras de compatibilidade numérica e casos especiais
                    numeric = {'int','float','decimal'}
                    if expected_type in numeric and rhs_type in numeric:
                        # Permite promoções numéricas (int->float/decimal, float<->decimal)
                        return
                    if expected_type == 'Nbase' and rhs_type == 'char':
                        return
                    # Caso contrário, erro SEM015
                    self.error_handler.report_error(SemanticError(
                        f"Tipo incompatível na atribuição: '{expected_type}' := '{rhs_type}'",
                        line, col, "SEM015"
                    ))

        elif isinstance(alvo, (AcessoCampo, AcessoArray)):
            # Analisa o acesso para obter o tipo do alvo (LHS type)
            # O _analyze_expr faz as checagens de acesso e retorna o tipo do valor acessado
            alvo_type = self._analyze_expr(alvo)

            # SEM015: Checagem de compatibilidade de tipo (do acesso com o RHS)
            if alvo_type != 'unknown_type' and rhs_type != 'unknown_type':
                if alvo_type != rhs_type:
                    numeric = {'int','float','decimal'}
                    if alvo_type in numeric and rhs_type in numeric:
                        return
                    if alvo_type == 'Nbase' and rhs_type == 'char':
                        return
                    self.error_handler.report_error(SemanticError(
                        f"Tipo incompatível na atribuição por acesso: '{alvo_type}' := '{rhs_type}'",
                        line, col, "SEM015"
                    ))

    def _analyze_if(self, node: InstrucaoIf):
        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        # SEM018: Condição deve ser bool
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

        # SEM018: Condição deve ser bool
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

        # Inicialização (sempre é uma atribuição)
        self._analyze_stmt(node.inicializacao)

        cond_type = self._analyze_expr(node.condicao)
        line, col = self._get_coords(node.condicao)

        # SEM018: Condição deve ser bool
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
            return _infer_literal_type(expr.valor)

        if isinstance(expr, Variavel):
            var_symbol = self.current_scope.lookup(expr.nome)
            if var_symbol is None:
                # SEM003: Variável não definida
                self.error_handler.report_error(SemanticError(
                    f"Uso de variável não definida: '{expr.nome}'", line, col, "SEM003"))
                return 'unknown_type'
            return var_symbol.type

        elif isinstance(expr, ExpressaoBinaria):
            left_type = self._analyze_expr(expr.esquerda)
            right_type = self._analyze_expr(expr.direita)

            result_type = _get_binary_result_type(expr.operador, left_type, right_type)

            if result_type is None:
                # SEM010: Tipos incompatíveis para operação
                self.error_handler.report_error(SemanticError(
                    f"Tipos incompatíveis '{left_type}' e '{right_type}' para o operador binário '{expr.operador}'.", line, col, "SEM010"))
                return 'unknown_type'

            return result_type

        elif isinstance(expr, ExpressaoUnaria):
            right_type = self._analyze_expr(expr.direita)

            if expr.operador in {'+', '-'}: # Negação numérica
                if right_type not in {'int', 'float'}:
                    # SEM011: Tipo inválido para operador unário
                    self.error_handler.report_error(SemanticError(
                        f"Operador unário '{expr.operador}' requer tipo numérico, recebeu '{right_type}'.", line, col, "SEM011"))
                    return 'unknown_type'
                return right_type

            elif expr.operador == '!': # Negação booleana
                if right_type != 'bool':
                    # SEM011: Tipo inválido para operador unário
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
                    # Se não é função, tenta tratar como construção de classe: Classe()
                    class_symbol = self.current_scope.lookup(fn_name) or self.global_scope.lookup(fn_name)
                    if class_symbol and class_symbol.kind == 'class':
                        # Analisa os argumentos (efeitos colaterais de tipos)
                        for a in expr.argumentos:
                            self._analyze_expr(a)
                        return class_symbol.type
                    # SEM005: Função não definida
                    self.error_handler.report_error(SemanticError(
                        f"Chamada para função não definida: '{fn_name}'", line, col, "SEM005"))
                    func_symbol = None
                else:
                    # SEM009: Número errado de argumentos
                    expected = getattr(func_symbol, 'param_count', 0)
                    got = len(expr.argumentos) if expr.argumentos else 0
                    if expected != got:
                        self.error_handler.report_error(SemanticError(
                            f"Função '{fn_name}' espera {expected} args mas recebeu {got}", line, col, "SEM009"))

            # Analisa os argumentos (necessário para inferir tipos de subexpressões)
            for a in expr.argumentos:
                self._analyze_expr(a)

            # Retorna o tipo de retorno da função (se encontrada)
            return func_symbol.type if func_symbol else 'unknown_type'

        elif isinstance(expr, AcessoArray):
            alvo_type = self._analyze_expr(expr.alvo)
            index_type = self._analyze_expr(expr.indice)
            line, col = self._get_coords(expr)

            # SEM017: Índice do array deve ser int
            if index_type != 'int':
                self.error_handler.report_error(SemanticError(
                    f"O índice do array deve ser do tipo 'int', recebeu '{index_type}'.", line, col, "SEM017"
                ))

            # SEM029: Tentativa de indexar tipo não-array
            if not alvo_type.startswith('Array<'):
                 self.error_handler.report_error(SemanticError(
                    f"Tentativa de indexar um tipo não-array: '{alvo_type}'.", line, col, "SEM029"
                ))
                 return 'unknown_type'

            # Retorna o tipo do elemento (ex: Array<Int> -> Int)
            return alvo_type[6:-1]

        elif isinstance(expr, AcessoCampo):
            alvo_type = self._analyze_expr(expr.alvo)
            field_name = expr.campo
            line, col = self._get_coords(expr)

            # Busca a definição do tipo (classe) no escopo global
            class_symbol = self.global_scope.lookup(alvo_type)

            if class_symbol is None or class_symbol.kind != 'class':
                # SEM026: Acesso a campo de tipo primitivo ou indefinido
                self.error_handler.report_error(SemanticError(
                    f"Acesso a campo ('{field_name}') de tipo inválido ou indefinido: '{alvo_type}'.", 
                    line, col, "SEM026"
                ))
                return 'unknown_type'

            # Checar se o campo existe na classe
            class_fields = getattr(class_symbol, 'fields', {})
            if field_name not in class_fields:
                # SEM028: Campo inexistente
                self.error_handler.report_error(SemanticError(
                    f"Campo '{field_name}' não existe na classe '{alvo_type}'.", 
                    line, col, "SEM028"
                ))
                return 'unknown_type'

            # Retorna o tipo do campo
            return class_fields[field_name]

        elif isinstance(expr, CriacaoClasse):
            # Analisa argumentos do construtor (se houver)
            for a in expr.argumentos:
                self._analyze_expr(a)
            # Retorna o nome da classe
            return expr.classe

        elif isinstance(expr, CriacaoArray):
            # Analisa o tamanho
            size_type = self._analyze_expr(expr.tamanho)
            if size_type != 'int':
                # SEM030: Tamanho do array deve ser int
                self.error_handler.report_error(SemanticError(
                    f"O tamanho do array deve ser do tipo 'int', recebido '{size_type}'.", line, col, "SEM030"
                ))

            # Retorna o tipo do array no formato 'Array<Tipo>'
            return f'Array<{expr.tipo}>'

        # Caso de fallback
        return 'unknown_type'