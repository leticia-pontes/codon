from typing import List, Any, Optional
from ...lexer.tokens import TokenStream, Token, KEYWORDS
from ..ast.ast_base import Programa, DeclaracaoFuncao, DeclaracaoClasse, ASTNode
from ..ast.declaracoes import VarDecl, PrintStmt, IfStmt, WhileStmt, Block, FunctionDecl, Parameter, ExprStmt, ReturnStmt
from ..ast.expressoes import Assignment, Binary, Unary, Literal, Identifier, Call, Grouping, IndexAccess, MemberAccess, Designator
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

    def parse(self) -> Programa:
        # CORREÇÃO: Ponto de entrada modificado para aceitar declarações diretamente no topo do arquivo.
        """Ponto de entrada: Programa := { DeclTopo }"""
        try:
            # Lógica de 'program Ident { ... }' REMOVIDA
            declarations = self.decl_topo()

            # Espera o fim do arquivo (EOF)
            self.tokens.expect('EOF')

            return Programa(declaracoes=declarations)

        except SyntaxError as e:
            self.error_handler.report_error(e)
            self.synchronize()
            return Programa(declaracoes=[])

    # ------------------ Declarações Topo ------------------

    def synchronize(self):
        """Heurística de recuperação de erro."""
        self.tokens.next() # Consome o token problemático

        # CORRIGIDO: Usando .tipo
        while self.tokens.peek().tipo != 'EOF':
            # CORRIGIDO: Usando .tipo
            tipo = self.tokens.peek().tipo
            if tipo == 'SEMI':
                self.tokens.next()
                return

            # CORRIGIDO: Usando .valor e .tipo
            # Sincroniza em tokens que iniciam uma declaração/comando
            # ADIÇÃO: 'class' na sincronização
            if (tipo == 'KWD' and self.tokens.peek().valor in ('var', 'const', 'void', 'if', 'while', 'class')) or \
                (tipo == 'RBRACE'):
                return
            self.tokens.next()

    def decl_topo(self) -> List[ASTNode]:
        # CORREÇÃO: Adicionado suporte a 'class' e comandos de topo.
        """DeclTopo := { DeclVarConst | DeclMetodo | DeclClasse | Statement }"""
        declarations = []
        # CORRIGIDO: Usando .tipo
        while self.tokens.peek().tipo != 'RBRACE' and self.tokens.peek().tipo != 'EOF':
            try:
                token = self.tokens.peek()
                token_tipo = token.tipo
                token_valor = token.valor if token_tipo == 'KWD' else None

                if token_tipo == 'KWD' and token_valor in ('const', 'var'):
                    declarations.append(self.decl_var_const())
                elif token_tipo == 'KWD' and token_valor == 'void':
                    declarations.append(self.decl_metodo())
                elif token_tipo == 'KWD' and token_valor == 'class':
                    # Novo: Tratamento para 'class'
                    declarations.append(self.decl_classe())
                # Novo: Tratamento para comandos de topo (para arquivos como hello_world.cd)
                elif token_valor in ('if', 'while', 'return', 'print') or token_tipo in ('ID', 'LPAREN', 'LBRACE', 'SEMI'):
                    declarations.append(self.statement())
                else:
                    # Caractere/token inesperado no topo.
                    raise SyntaxError(f"Esperado declaração de topo (const, var, void, class) ou comando, mas chegou '{token.valor}' ({token_tipo}).", token.linha, token.coluna)
            except SyntaxError as e:
                self.error_handler.report_error(e)
                self.synchronize() # Tenta se recuperar para continuar a próxima iteração

        return declarations

    def decl_var_const(self) -> VarDecl:
        """Decl := DeclConst | DeclVar"""
        token = self.tokens.peek()
        # CORRIGIDO: Usando .tipo e .valor
        if token.tipo == 'KWD' and token.valor == 'const':
            return self.decl_const()
        elif token.tipo == 'KWD' and token.valor == 'var':
            return self.decl_var()

        # CORRIGIDO: Usando .linha, .coluna
        raise SyntaxError("Esperado 'const' ou 'var'.", token.linha, token.coluna)

    def decl_const(self) -> VarDecl:
        """DeclConst := "const" Tipo Ident "=" ConstLit ";" """
        # CORRIGIDO: Usando .valor, .linha, .coluna
        const_token = self.tokens.expect('KWD')
        if const_token.valor != 'const':
            raise SyntaxError(f"Esperado 'const', mas chegou '{const_token.valor}'.", const_token.linha, const_token.coluna)

        var_type = self.tokens.expect('ID') # Tipo é apenas um ID por enquanto
        identifier = self.tokens.expect('ID')
        self.tokens.expect('ASSIGN') # '='

        # O parser simplificado não implementará ConstLit, apenas a Expressao
        initial_value = self.expression()

        self.tokens.expect('SEMI')
        # CORRIGIDO: Usando .valor
        return VarDecl(token=const_token, identifier=identifier, var_type=var_type.valor, initial_value=initial_value, is_mutable=False)

    def decl_var(self) -> VarDecl:
        """DeclVar := "var" Tipo Ident { "," Ident } ";" (Simplificado para 1 var)"""
        # CORRIGIDO: Usando .valor, .linha, .coluna
        var_token = self.tokens.expect('KWD')
        if var_token.valor != 'var':
            raise SyntaxError(f"Esperado 'var', mas chegou '{var_token.valor}'.", var_token.linha, var_token.coluna)
            
        var_type = self.tokens.expect('ID')
        identifier = self.tokens.expect('ID')

        # Ignorando a lista de identificadores para simplificar
        # A atribuição inicial não é permitida em DeclVar na gramática BNF/EBNF fornecida, mas é comum

        self.tokens.expect('SEMI')
        # CORRIGIDO: Usando .valor
        return VarDecl(token=var_token, identifier=identifier, var_type=var_type.valor, initial_value=None, is_mutable=True)

    def decl_metodo(self) -> FunctionDecl:
        """DeclMetodo := "void" Ident "(" ParamsFormOpt ")" { DeclVar } Bloco"""
        # CORRIGIDO: Usando .valor, .linha, .coluna
        void_token = self.tokens.expect('KWD')
        if void_token.valor != 'void':
            raise SyntaxError(f"Esperado 'void', mas chegou '{void_token.valor}'.", void_token.linha, void_token.coluna)
            
        name = self.tokens.expect('ID')
        self.tokens.expect('LPAREN')

        params = self.params_form_opt()
        self.tokens.expect('RPAREN')

        # Ignorando { DeclVar } - declarações locais vão no início do Bloco para simplicidade

        body = self.bloco()

        return FunctionDecl(token=void_token, name=name, params=params, body=body, return_type='void')

    # NOVO: Implementação para a declaração de classes que estava faltando
    def decl_classe(self) -> DeclaracaoClasse:
        """DeclClasse := 'class' Ident [ 'extends' Ident ] '{' { Decl | DeclMetodo } '}'"""
        class_token = self.tokens.expect('KWD') # Consome 'class'
        # Checagem extra de segurança
        if class_token.valor != 'class':
            raise SyntaxError(f"Esperado 'class', mas chegou '{class_token.valor}'.", class_token.linha, class_token.coluna)
        
        name = self.tokens.expect('ID')
        
        # Extends opcional
        superclass = None
        peeked = self.tokens.peek()
        if peeked.tipo == 'KWD' and peeked.valor == 'extends':
             self.tokens.next() # Consome 'extends'
             superclass = self.tokens.expect('ID')
             
        self.tokens.expect('LBRACE')
        
        # Corpo da classe - Membros (apenas variáveis e métodos são considerados aqui)
        members = []
        while self.tokens.peek().tipo != 'RBRACE' and self.tokens.peek().tipo != 'EOF':
            try:
                token = self.tokens.peek()
                token_tipo = token.tipo
                token_valor = token.valor if token_tipo == 'KWD' else None

                if token_tipo == 'KWD' and token_valor in ('const', 'var'):
                    members.append(self.decl_var_const())
                elif token_tipo == 'KWD' and token_valor == 'void':
                    members.append(self.decl_metodo())
                else:
                    # Caractere/token inesperado.
                    raise SyntaxError(f"Esperado 'const', 'var' ou 'void' dentro da classe, mas chegou '{token.valor}'.", token.linha, token.coluna)
            except SyntaxError as e:
                self.error_handler.report_error(e)
                self.synchronize()

        self.tokens.expect('RBRACE')
        
        # Retorna o nó AST da classe
        return DeclaracaoClasse(token=class_token, name=name, superclass=superclass, members=members)

    def params_form_opt(self) -> List[Parameter]:
        """ParamsFormOpt := ParamsForm | ε"""
        # CORRIGIDO: Usando .tipo
        if self.tokens.peek().tipo == 'RPAREN':
            return []
        return self.params_form()

    def params_form(self) -> List[Parameter]:
        """ParamsForm := Tipo Ident { "," Tipo Ident }"""
        params = []
        param_type_token = self.tokens.expect('ID') # Tipo é um ID
        param_name_token = self.tokens.expect('ID')
        # CORRIGIDO: Usando .valor
        params.append(Parameter(token=param_type_token, name=param_name_token, param_type=param_type_token.valor))

        while self.tokens.accept('COMMA'):
            param_type_token = self.tokens.expect('ID')
            param_name_token = self.tokens.expect('ID')
            # CORRIGIDO: Usando .valor
            params.append(Parameter(token=param_type_token, name=param_name_token, param_type=param_type_token.valor))

        return params

    # ------------------ Comandos ------------------

    def statement(self) -> ASTNode:
        """SeqComando := { Comando } - Comando é o lookahead principal"""
        token = self.tokens.peek()
        # CORRIGIDO: Usando .tipo e .valor
        token_tipo = token.tipo
        token_valor = token.valor if token_tipo == 'KWD' else None

        if token_valor == 'if':
            return self.comando_if()
        elif token_valor == 'while':
            return self.comando_while()
        elif token_valor == 'return':
            return self.comando_return()
        elif token_valor == 'read':
            # return self.comando_read() # Não implementado
            # ADIÇÃO: Consumir token 'read' para evitar loop infinito em caso de falta de implementação
            self.tokens.expect('KWD')
            # Adicionar lógica de sincronização ou tratamento de erro adequado aqui se 'read' for encontrado
            # Por enquanto, lança erro para forçar sincronização
            raise SyntaxError(f"Comando 'read' não implementado.", token.linha, token.coluna)
        elif token_valor == 'print':
            return self.comando_print()
        # CORRIGIDO: Usando .tipo
        elif token_tipo == 'LBRACE':
            return self.bloco()
        elif token_tipo == 'SEMI':
            return self.comando_vazio()
        else:
            # Deve ser ComandoDesignador (atribuição, chamada, ++/--) ou ExprStmt
            # Vamos tratar como uma expressão seguida de ';' (simplificado)
            return self.comando_designador_ou_expr()

        # CORRIGIDO: Usando .valor, .tipo, .linha, .coluna
        # Fallback para expressão (que deve ser tratada como erro se não for uma expressão válida)
        # Este raise só será atingido se as condições acima falharem E o comando_designador_ou_expr falhar
        raise SyntaxError(f"Esperado início de comando, mas chegou '{token.valor}' ({token_tipo}).", token.linha, token.coluna)

    def bloco(self) -> Block:
        """Bloco := "{" SeqComando "}" """
        l_brace = self.tokens.expect('LBRACE')

        statements = []
        # CORRIGIDO: Usando .tipo
        while self.tokens.peek().tipo != 'RBRACE' and self.tokens.peek().tipo != 'EOF':
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
        # CORRIGIDO: Usando .valor, .linha, .coluna
        if_token = self.tokens.expect('KWD')
        if if_token.valor != 'if':
            raise SyntaxError(f"Esperado 'if', mas chegou '{if_token.valor}'.", if_token.linha, if_token.coluna)
            
        self.tokens.expect('LPAREN')
        condition = self.condicao()
        self.tokens.expect('RPAREN')

        then_branch = self.statement()

        else_branch = None
        # CORRIGIDO: Usando .tipo e .valor para verificar a palavra-chave 'else'
        token = self.tokens.peek()
        if token.tipo == 'KWD' and token.valor == 'else':
            self.tokens.next() # Consome 'else'
            else_branch = self.statement()

        return IfStmt(token=if_token, condition=condition, then_branch=then_branch, else_branch=else_branch)

    def comando_while(self) -> WhileStmt:
        """ComandoWhile := "while" "(" Condicao ")" Comando"""
        # CORRIGIDO: Usando .valor, .linha, .coluna
        while_token = self.tokens.expect('KWD')
        if while_token.valor != 'while':
            raise SyntaxError(f"Esperado 'while', mas chegou '{while_token.valor}'.", while_token.linha, while_token.coluna)
            
        self.tokens.expect('LPAREN')
        condition = self.condicao()
        self.tokens.expect('RPAREN')

        body = self.statement()

        return WhileStmt(token=while_token, condition=condition, body=body)

    def comando_return(self) -> ReturnStmt:
        """ComandoReturn := "return" [ Expressao ] ";" """
        # CORRIGIDO: Usando .valor, .linha, .coluna
        return_token = self.tokens.expect('KWD')
        if return_token.valor != 'return':
            raise SyntaxError(f"Esperado 'return', mas chegou '{return_token.valor}'.", return_token.linha, return_token.coluna)

        # CORRIGIDO: Usando .tipo
        value = None
        if self.tokens.peek().tipo != 'SEMI':
            value = self.expression()

        self.tokens.expect('SEMI')
        return ReturnStmt(token=return_token, value=value)

    def comando_print(self) -> PrintStmt:
        """ComandoPrint := "print" "(" Expressao [ "," Numero ] ")" ";" """
        # CORRIGIDO: Usando .valor, .linha, .coluna
        print_token = self.tokens.expect('KWD')
        if print_token.valor != 'print':
            raise SyntaxError(f"Esperado 'print', mas chegou '{print_token.valor}'.", print_token.linha, print_token.coluna)
            
        self.tokens.expect('LPAREN')
        expression = self.expression()

        if self.tokens.accept('COMMA'):
            # Numero é apenas uma expressão primária que resolve para um número
            width = self.expression()
        else:
             width = None # Adicionado 'else' para clareza (a lógica era a mesma)

        self.tokens.expect('RPAREN')
        self.tokens.expect('SEMI')

        return PrintStmt(token=print_token, expression=expression, width=width)

    def comando_designador_ou_expr(self) -> ASTNode:
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

    def condicao(self) -> ASTNode:
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
        # CORRIGIDO: Usando .linha, .coluna
        raise SyntaxError("Esperado operador relacional (==, !=, >, >=, <, <=).", token.linha, token.coluna)

    def expression(self) -> ASTNode:
        """expression := assignment (nível mais baixo de precedência)"""
        return self.assignment()

    def assignment(self) -> ASTNode:
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

            # CORRIGIDO: Usando .linha, .coluna
            self.error_handler.report_error(SyntaxError("Alvo de atribuição inválido (não é designador).", assign_token.linha, assign_token.coluna))
            return value

        return expr

    # logic_or (||)
    def logic_or(self) -> ASTNode:
        """logic_or := logic_and { '||' logic_and }"""
        expr = self.logic_and()
        while self.tokens.accept('OR_OR'):
            operator = self.tokens.current()
            right = self.logic_and()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # logic_and (&&)
    def logic_and(self) -> ASTNode:
        """logic_and := comparison { '&&' comparison }"""
        # A gramática original não tem AND/OR lógicos, mas usamos aqui.
        expr = self.comparison()
        while self.tokens.accept('AND_AND'):
            operator = self.tokens.current()
            right = self.comparison()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # comparison/equality (==, !=, <, <=, >, >=)
    def comparison(self) -> ASTNode:
        """comparison := term { OpRel term }"""
        expr = self.term_soma() # Nível de soma

        # CORRIGIDO: Usando .tipo
        while self.tokens.peek().tipo in ('EQ', 'NE', 'GT', 'GE', 'LT', 'LE'):
            operator = self.op_rel()
            right = self.term_soma()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # term (+, -)
    def term_soma(self) -> ASTNode:
        """Expressao := [ "-" ] Termo { OpSoma Termo }"""
        # Tratamento do Unário de Subtração (na verdade, é o nível Unary que lida com isso)
        expr = self.term_mult()

        while self.tokens.accept('PLUS', 'MINUS'):
            operator = self.tokens.current()
            right = self.term_mult()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # factor (*, /, %)
    def term_mult(self) -> ASTNode:
        """Termo := Fator { OpMult Fator }"""
        expr = self.unary()

        while self.tokens.accept('STAR', 'SLASH', 'PERCENT'):
            operator = self.tokens.current()
            right = self.unary()
            expr = Binary(token=operator, left=expr, operator=operator, right=right)
        return expr

    # unary (-, !)
    def unary(self) -> ASTNode:
        """unary := ( '!' | '-' ) unary | call"""

        if self.tokens.accept('BANG', 'MINUS'):
            operator = self.tokens.current()
            right = self.unary() # Associatividade R->L
            return Unary(token=operator, operator=operator, right=right)

        return self.call_or_designator()

    # Call e Designador (Propriedade, Array Access)
    def call_or_designator(self) -> ASTNode:
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
            elif self.tokens.peek().tipo == 'PLUS' and self.tokens.peek_next().tipo == 'PLUS':
                # Usa a lógica de accept para consumir ++
                self.tokens.next() # Consome o primeiro '+'
                op_token = self.tokens.next() # Consome o segundo '+' (token 'PLUS')
                # Simplificação: Usar um operador Unary para ++
                expr = Unary(token=op_token, operator=op_token, right=expr)
            
            elif self.tokens.peek().tipo == 'MINUS' and self.tokens.peek_next().tipo == 'MINUS':
                # Usa a lógica de accept para consumir --
                self.tokens.next() # Consome o primeiro '-'
                op_token = self.tokens.next() # Consome o segundo '-' (token 'MINUS')
                # Simplificação: Usar um operador Unary para --
                expr = Unary(token=op_token, operator=op_token, right=expr)

            else:
                break

        return expr

    def params_ativos_opt(self) -> List[ASTNode]:
        """ParamsAtivosOpt := ParamsAtivos | ε"""
        # CORRIGIDO: Usando .tipo
        if self.tokens.peek().tipo == 'RPAREN':
            return []
        return self.params_ativos()

    def params_ativos(self) -> List[ASTNode]:
        """ParamsAtivos := Expressao { "," Expressao }"""
        arguments = [self.expression()]
        while self.tokens.accept('COMMA'):
            arguments.append(self.expression())
        return arguments

    # primary (literals, identifiers, grouping, new array)
    def primary(self) -> ASTNode:
        """Fator := Designador | Designador() | Literal | ConstBool | "new" Tipo "[" Exp "]" | "(" Exp ")" """

        token = self.tokens.peek()
        # CORRIGIDO: Usando .tipo
        token_tipo = token.tipo

        # Literais
        if token_tipo in ('DEC_INT', 'FLOAT', 'STRING', 'DNA_LIT', 'RNA_LIT', 'PROT_LIT', 'CHAR'):
            self.tokens.next()
            return Literal(token=token, value=token.literal)

        # Booleanos (Palavras-chave 'true'/'false')
        # CORRIGIDO: Usando .tipo e .valor
        if token_tipo == 'KWD' and token.valor in ('true', 'false'):
            self.tokens.next()
            return Literal(token=token, value=(token.valor == 'true'))

        # Agrupamento (Parênteses)
        # CORRIGIDO: Usando .tipo
        if token_tipo == 'LPAREN':
            self.tokens.next()
            expr = self.expression()
            self.tokens.expect('RPAREN')

            return Grouping(token=token, expression=expr)

        # Novo Array: "new" Tipo "[" Expressao "]"
        # CORRIGIDO: Usando .tipo e .valor

        if token_tipo == 'KWD' and token.valor == 'new':
            new_token = self.tokens.next()
            var_type = self.tokens.expect('ID')
            self.tokens.expect('LBRACK')
            size_expr = self.expression()
            self.tokens.expect('RBRACK')
            # CORRIGIDO: Usando .valor
            return Call(token=new_token, callee=Identifier(token=var_type, name='new_array'), arguments=[Identifier(token=var_type, name=var_type.valor), size_expr])

        # Identificadores
        # CORRIGIDO: Usando .tipo
        if token_tipo == 'ID':
            self.tokens.next()
            # CORRIGIDO: Usando .valor
            return Designator(token=token, name=token.valor) # Designator é uma subclasse de Identifier

        # CORRIGIDO: Usando .valor, .tipo, .linha, .coluna
        # Se não casar nada, lança erro
        raise SyntaxError(f"Esperado expressão primária (Literal, ID, '(', 'new'), mas chegou '{token.valor}' ({token_tipo}).", token.linha, token.coluna)