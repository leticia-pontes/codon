from typing import List, Any, Optional
from ...lexer.tokens import TokenStream, Token, KEYWORDS
from ...ast.ast_base import Program, Declaration, Statement, Expression
from ...ast.declaracoes import VarDecl, PrintStmt, IfStmt, WhileStmt, Block, FunctionDecl, Parameter, ExprStmt, ReturnStmt
from ...ast.expressoes import Assignment, Binary, Unary, Literal, Identifier, Call, Grouping, IndexAccess, MemberAccess, Designator
from ...utils.erros import SyntaxError, ErrorHandler

class ParserLL1:
    """
    Implementa um Parser Descendente Recursivo para a gramática Codon.
    Sincronização básica baseada em ';' e palavras-chave de declaração.
    """
    def __init__(self, token_stream: TokenStream, error_handler: ErrorHandler):
        self.tokens = token_stream
        self.error_handler = error_handler
        self.start_token = self.tokens.peek()

    def parse(self) -> Program:
        """Ponto de entrada: Programa := "program" Ident "{" DeclTopo "}" """
        try:
            self.tokens.expect('KWD', 'program')
            program_name = self.tokens.expect('ID')
            self.tokens.expect('LBRACE')

            declarations = self.decl_topo()

            self.tokens.expect('RBRACE')
            self.tokens.expect('EOF')

            return Program(token=program_name, statements=declarations)

        except SyntaxError as e:
            self.error_handler.report_error(e)
            self.synchronize()
            return Program(token=self.start_token, statements=[])

    # ------------------ Declarações Topo ------------------

    def synchronize(self):
        """Heurística de recuperação de erro."""
        self.tokens.next() # Consome o token problemático

        while self.tokens.peek().kind != 'EOF':
            kind = self.tokens.peek().kind
            if kind == 'SEMI':
                self.tokens.next()
                return

            # Sincroniza em tokens que iniciam uma declaração/comando
            if (kind == 'KWD' and self.tokens.peek().lexeme in ('var', 'const', 'void', 'if', 'while')) or \
               (kind == 'RBRACE'):
                return

            self.tokens.next()

    def decl_topo(self) -> List[Declaration]:
        """DeclTopo := { Decl | DeclMetodo }"""
        declarations = []
        while self.tokens.peek().kind != 'RBRACE' and self.tokens.peek().kind != 'EOF':
            try:
                # O lookahead deve distinguir Decl (const/var) de DeclMetodo (void)
                token = self.tokens.peek()
                if token.kind == 'KWD' and token.lexeme in ('const', 'var'):
                    declarations.append(self.decl_var_const())
                elif token.kind == 'KWD' and token.lexeme == 'void':
                    declarations.append(self.decl_metodo())
                else:
                    # Caractere/token inesperado no topo.
                    raise SyntaxError(f"Esperado 'const', 'var' ou 'void' no topo, mas chegou '{token.lexeme}'.", token.line, token.col)
            except SyntaxError as e:
                self.error_handler.report_error(e)
                self.synchronize() # Tenta se recuperar para continuar a próxima iteração

        return declarations

    def decl_var_const(self) -> Declaration:
        """Decl := DeclConst | DeclVar"""
        token = self.tokens.peek()
        if token.kind == 'KWD' and token.lexeme == 'const':
            return self.decl_const()
        elif token.kind == 'KWD' and token.lexeme == 'var':
            return self.decl_var()

        # Este caso não deve ser alcançado se decl_topo for correto
        raise SyntaxError("Esperado 'const' ou 'var'.", token.line, token.col)

    def decl_const(self) -> VarDecl:
        """DeclConst := "const" Tipo Ident "=" ConstLit ";" """
        const_token = self.tokens.expect('KWD', 'const')
        var_type = self.tokens.expect('ID') # Tipo é apenas um ID por enquanto
        identifier = self.tokens.expect('ID')
        self.tokens.expect('ASSIGN') # '='

        # O parser simplificado não implementará ConstLit, apenas a Expressao
        initial_value = self.expression()

        self.tokens.expect('SEMI')
        return VarDecl(token=const_token, identifier=identifier, var_type=var_type.lexeme, initial_value=initial_value, is_mutable=False)

    def decl_var(self) -> VarDecl:
        """DeclVar := "var" Tipo Ident { "," Ident } ";" (Simplificado para 1 var)"""
        var_token = self.tokens.expect('KWD', 'var')
        var_type = self.tokens.expect('ID')
        identifier = self.tokens.expect('ID')

        # Ignorando a lista de identificadores para simplificar
        # A atribuição inicial não é permitida em DeclVar na gramática BNF/EBNF fornecida, mas é comum

        self.tokens.expect('SEMI')
        return VarDecl(token=var_token, identifier=identifier, var_type=var_type.lexeme, initial_value=None, is_mutable=True)

    def decl_metodo(self) -> FunctionDecl:
        """DeclMetodo := "void" Ident "(" ParamsFormOpt ")" { DeclVar } Bloco"""
        void_token = self.tokens.expect('KWD', 'void')
        name = self.tokens.expect('ID')
        self.tokens.expect('LPAREN')

        params = self.params_form_opt()
        self.tokens.expect('RPAREN')

        # Ignorando { DeclVar } - declarações locais vão no início do Bloco para simplicidade

        body = self.bloco()

        return FunctionDecl(token=void_token, name=name, params=params, body=body, return_type='void')

    def params_form_opt(self) -> List[Parameter]:
        """ParamsFormOpt := ParamsForm | ε"""
        if self.tokens.peek().kind == 'RPAREN':
            return []
        return self.params_form()

    def params_form(self) -> List[Parameter]:
        """ParamsForm := Tipo Ident { "," Tipo Ident }"""
        params = []
        param_type_token = self.tokens.expect('ID') # Tipo é um ID
        param_name_token = self.tokens.expect('ID')
        params.append(Parameter(token=param_type_token, name=param_name_token, param_type=param_type_token.lexeme))

        while self.tokens.accept('COMMA'):
            param_type_token = self.tokens.expect('ID')
            param_name_token = self.tokens.expect('ID')
            params.append(Parameter(token=param_type_token, name=param_name_token, param_type=param_type_token.lexeme))

        return params

    # ------------------ Comandos ------------------

    def statement(self) -> Statement:
        """SeqComando := { Comando } - Comando é o lookahead principal"""
        token = self.tokens.peek()
        token_lexeme = token.lexeme if token.kind == 'KWD' else None

        if token_lexeme == 'if':
            return self.comando_if()
        elif token_lexeme == 'while':
            return self.comando_while()
        elif token_lexeme == 'return':
            return self.comando_return()
        elif token_lexeme == 'read':
            # return self.comando_read() # Não implementado
            pass
        elif token_lexeme == 'print':
            return self.comando_print()
        elif token.kind == 'LBRACE':
            return self.bloco()
        elif token.kind == 'SEMI':
            return self.comando_vazio()
        else:
            # Deve ser ComandoDesignador (atribuição, chamada, ++/--) ou ExprStmt
            # Vamos tratar como uma expressão seguida de ';' (simplificado)
            return self.comando_designador_ou_expr()

        # Fallback para expressão (que deve ser tratada como erro se não for uma expressão válida)
        raise SyntaxError(f"Esperado início de comando, mas chegou '{token.lexeme}'.", token.line, token.col)

    def bloco(self) -> Block:
        """Bloco := "{" SeqComando "}" """
        l_brace = self.tokens.expect('LBRACE')

        statements = []
        while self.tokens.peek().kind != 'RBRACE' and self.tokens.peek().kind != 'EOF':
            try:
                statements.append(self.statement())
            except SyntaxError as e:
                self.error_handler.report_error(e)
                self.synchronize() # Tenta se recuperar

        self.tokens.expect('RBRACE')
        return Block(token=l_brace, statements=statements)

    def comando_vazio(self) -> ExprStmt:
        """Comando vazio: ';'"""
        semi = self.tokens.expect('SEMI')
        return ExprStmt(token=semi, expression=Literal(token=semi, value=None))

    def comando_if(self) -> IfStmt:
        """ComandoIf := "if" "(" Condicao ")" Comando [ "else" Comando ]"""
        if_token = self.tokens.expect('KWD', 'if')
        self.tokens.expect('LPAREN')
        condition = self.condicao()
        self.tokens.expect('RPAREN')

        then_branch = self.statement()

        else_branch = None
        if self.tokens.accept('KWD', 'else'):
            else_branch = self.statement()

        return IfStmt(token=if_token, condition=condition, then_branch=then_branch, else_branch=else_branch)

    def comando_while(self) -> WhileStmt:
        """ComandoWhile := "while" "(" Condicao ")" Comando"""
        while_token = self.tokens.expect('KWD', 'while')
        self.tokens.expect('LPAREN')
        condition = self.condicao()
        self.tokens.expect('RPAREN')

        body = self.statement()

        return WhileStmt(token=while_token, condition=condition, body=body)

    def comando_return(self) -> ReturnStmt:
        """ComandoReturn := "return" [ Expressao ] ";" """
        return_token = self.tokens.expect('KWD', 'return')

        value = None
        if self.tokens.peek().kind != 'SEMI':
            value = self.expression()

        self.tokens.expect('SEMI')
        return ReturnStmt(token=return_token, value=value)

    def comando_print(self) -> PrintStmt:
        """ComandoPrint := "print" "(" Expressao [ "," Numero ] ")" ";" """
        print_token = self.tokens.expect('KWD', 'print')
        self.tokens.expect('LPAREN')

        expression = self.expression()

        width = None
        if self.tokens.accept('COMMA'):
            # Numero é apenas uma expressão primária que resolve para um número
            width = self.expression()

        self.tokens.expect('RPAREN')
        self.tokens.expect('SEMI')

        return PrintStmt(token=print_token, expression=expression, width=width)

    def comando_designador_ou_expr(self) -> Statement:
        """
        Trata: ComandoDesignador (atribuição, chamada, ++/--) ou ExprStmt
        No modelo LL(1), precisamos resolver o lookahead (Ident ...).
        Simplificação: Se a expressão for uma atribuição/chamada, é ComandoDesignador.
        """
        expr = self.expression()
        self.tokens.expect('SEMI')

        # Poderíamos ter lógica para verificar se `expr` é Call, Assignment, etc.
        # Por simplicidade, tudo é um ExprStmt, e a fase semântica validará o uso.
        return ExprStmt(token=expr.token, expression=expr)

    # ------------------ Condições e Expressões ------------------

    def condicao(self) -> Expression:
        """Condicao := Expressao OpRel Expressao"""
        left = self.expression()
        op_token = self.op_rel()
        right = self.expression()

        return Binary(token=op_token, left=left, operator=op_token, right=right)

    def op_rel(self) -> Token:
        """OpRel := "==" | "!=" | ">" | ">=" | "<" | "<=" """
        if self.tokens.accept('EQ', 'NE', 'GT', 'GE', 'LT', 'LE'):
            return self.tokens.current()

        token = self.tokens.peek()
        raise SyntaxError("Esperado operador relacional (==, !=, >, >=, <, <=).", token.line, token.col)

    def expression(self) -> Expression:
        """expression := assignment (nível mais baixo de precedência)"""
        return self.assignment()

    def assignment(self) -> Expression:
        """assignment := logic_or (OpAtrib logic_or) (Associatividade R->L)"""
        # Tenta casar o lado esquerdo, que pode ser o alvo de uma atribuição
        expr = self.logic_or()

        # OpAtrib é apenas '=' na gramática, mas incluímos compostos
        if self.tokens.accept('ASSIGN', 'PLUS_EQ', 'MINUS_EQ', 'STAR_EQ', 'SLASH_EQ'):
            assign_token = self.tokens.current()
            value = self.assignment() # Chamada recursiva para R->L

            # Verificação semântica do alvo (Designador)
            if isinstance(expr, (Identifier, IndexAccess, MemberAccess)):
                return Assignment(token=assign_token, target=expr, value=value)

            self.error_handler.report_error(SyntaxError("Alvo de atribuição inválido (não é designador).", assign_token.line, assign_token.col))
            return value

        return expr

    # logic_or (||)
    def logic_or(self) -> Expression:
        """logic_or := logic_and { '||' logic_and }"""
        expr = self.logic_and()
        while self.tokens.accept('OR_OR'):
            operator = self.tokens.current()
            right = self.logic_and()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # logic_and (&&)
    def logic_and(self) -> Expression:
        """logic_and := comparison { '&&' comparison }"""
        # A gramática original não tem AND/OR lógicos, mas usamos aqui.
        expr = self.comparison()
        while self.tokens.accept('AND_AND'):
            operator = self.tokens.current()
            right = self.comparison()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # comparison/equality (==, !=, <, <=, >, >=)
    def comparison(self) -> Expression:
        """comparison := term { OpRel term }"""
        expr = self.term_soma() # Nível de soma

        while self.tokens.peek().kind in ('EQ', 'NE', 'GT', 'GE', 'LT', 'LE'):
            operator = self.op_rel()
            right = self.term_soma()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # term (+, -)
    def term_soma(self) -> Expression:
        """Expressao := [ "-" ] Termo { OpSoma Termo }"""
        # Tratamento do Unário de Subtração (na verdade, é o nível Unary que lida com isso)
        expr = self.term_mult()

        while self.tokens.accept('PLUS', 'MINUS'):
            operator = self.tokens.current()
            right = self.term_mult()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # factor (*, /, %)
    def term_mult(self) -> Expression:
        """Termo := Fator { OpMult Fator }"""
        expr = self.unary()

        while self.tokens.accept('STAR', 'SLASH', 'PERCENT'):
            operator = self.tokens.current()
            right = self.unary()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # unary (-, !)
    def unary(self) -> Expression:
        """unary := ( '!' | '-' ) unary | call"""

        if self.tokens.accept('BANG', 'MINUS'):
            operator = self.tokens.current()
            right = self.unary() # Associatividade R->L
            return Unary(token=operator, operator=operator, right=right)

        return self.call_or_designator()

    # Call e Designador (Propriedade, Array Access)
    def call_or_designator(self) -> Expression:
        """
        Designador (prefixo): Designador | Designador "(" ParamsAtivosOpt ")"
        Designador := Ident { "." Ident | "[" Expressao "]" }
        """
        expr = self.primary()

        while True:
            # Chamada de Função/Método
            if self.tokens.accept('LPAREN'):
                open_paren = self.tokens.current()
                arguments = self.params_ativos_opt()
                close_paren = self.tokens.expect('RPAREN')

                expr = Call(token=close_paren, callee=expr, arguments=arguments)

            # Acesso a Membro (DOT)
            elif self.tokens.accept('DOT'):
                dot_token = self.tokens.current()
                member_id = self.tokens.expect('ID')
                expr = MemberAccess(token=dot_token, container=expr, member=member_id)

            # Acesso a Índice (LBRACK)
            elif self.tokens.accept('LBRACK'):
                open_bracket = self.tokens.current()
                index_expr = self.expression()
                self.tokens.expect('RBRACK')

                expr = IndexAccess(token=open_bracket, container=expr, index=index_expr)

            # Pós-fixos (++, --) da gramática
            elif self.tokens.accept('PLUS', 'PLUS') or self.tokens.accept('MINUS', 'MINUS'):
                # Simplificação: Usar um operador Unary para ++/--
                op_token = self.tokens.current()
                expr = Unary(token=op_token, operator=op_token, right=expr)

            else:
                break

        return expr

    def params_ativos_opt(self) -> List[Expression]:
        """ParamsAtivosOpt := ParamsAtivos | ε"""
        if self.tokens.peek().kind == 'RPAREN':
            return []
        return self.params_ativos()

    def params_ativos(self) -> List[Expression]:
        """ParamsAtivos := Expressao { "," Expressao }"""
        arguments = [self.expression()]
        while self.tokens.accept('COMMA'):
            arguments.append(self.expression())
        return arguments

    # primary (literals, identifiers, grouping, new array)
    def primary(self) -> Expression:
        """Fator := Designador | Designador() | Literal | ConstBool | "new" Tipo "[" Exp "]" | "(" Exp ")" """

        token = self.tokens.peek()
        token_kind = token.kind

        # Literais
        if token_kind in ('DEC_INT', 'FLOAT', 'STRING', 'DNA_LIT', 'RNA_LIT', 'PROT_LIT', 'CHAR'):
            self.tokens.next()
            return Literal(token=token, value=token.literal)

        # Booleanos (Palavras-chave 'true'/'false')
        if token_kind == 'KWD' and token.lexeme in ('true', 'false'):
            self.tokens.next()
            return Literal(token=token, value=(token.lexeme == 'true'))

        # Agrupamento (Parênteses)
        if token_kind == 'LPAREN':
            self.tokens.next()
            expr = self.expression()
            self.tokens.expect('RPAREN')
            return Grouping(token=token, expression=expr)

        # Novo Array: "new" Tipo "[" Expressao "]"
        if token_kind == 'KWD' and token.lexeme == 'new':
            new_token = self.tokens.next()
            var_type = self.tokens.expect('ID')
            self.tokens.expect('LBRACK')
            size_expr = self.expression()
            self.tokens.expect('RBRACK')
            # Não existe AST específica para 'new', tratamos como Call ou Literal (simplificado)
            return Call(token=new_token, callee=Identifier(token=var_type, name='new_array'), arguments=[Identifier(token=var_type, name=var_type.lexeme), size_expr])

        # Identificadores
        if token_kind == 'ID':
            self.tokens.next()
            return Designator(token=token, name=token.lexeme) # Designator é uma subclasse de Identifier

        # Se não casar nada, lança erro
        raise SyntaxError(f"Esperado expressão primária (Literal, ID, '(', 'new'), mas chegou '{token.lexeme}' ({token_kind}).", token.line, token.col)