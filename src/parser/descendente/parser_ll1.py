from typing import List, Any
# Não dependemos mais da implementação externa de TokenStream para a lógica de fluxo
from ...lexer.tokens import Token
from ..ast.ast_base import *
from ...utils.erros import SyntaxError, ErrorHandler

# --- Classe de Stream Interna para Garantir Funcionamento ---
class InternalTokenStream:
    def __init__(self, tokens: List[Any]):
        self.tokens = tokens
        self.pos = 0
        # Token EOF falso para segurança
        self.eof = type('Token', (), {'kind': 'EOF', 'lexeme': '', 'tipo': 'EOF', 'line': 0, 'col': 0, 'valor': ''})()

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.eof

    def next(self):
        if self.pos < len(self.tokens):
            tk = self.tokens[self.pos]
            self.pos += 1
            return tk # Retorna o que foi consumido
        return self.eof
        
    def expect(self, kind_or_lexeme):
        tk = self.peek()
        # Verifica por kind ou lexeme
        if tk.kind == kind_or_lexeme or tk.lexeme == kind_or_lexeme:
            self.next()
            return tk
        # Fallback para verificação genérica de ID
        if kind_or_lexeme == 'ID' and tk.kind == 'ID':
             self.next()
             return tk
        
        raise SyntaxError(f"Esperado '{kind_or_lexeme}', mas chegou '{tk.lexeme}' ({tk.kind})", tk.line, tk.col)

    def accept(self, kind, lexeme=None):
        tk = self.peek()
        if tk.kind == kind:
            if lexeme and tk.lexeme != lexeme: return False
            self.next()
            return True
        return False

# --- Parser ---
class Parser:
    def __init__(self, token_source: Any, error_handler: ErrorHandler):
        # Extrai a lista crua de tokens, não importa de onde venha
        raw_tokens = []
        if hasattr(token_source, 'tokens') and isinstance(token_source.tokens, list):
            raw_tokens = token_source.tokens
        elif isinstance(token_source, list):
            raw_tokens = token_source
        else:
            # Tenta acessar via iterador ou atributo interno
            try: raw_tokens = list(token_source.tokens)
            except: raw_tokens = []
            
        self.tokens = InternalTokenStream(raw_tokens)
        self.error_handler = error_handler
        self.start_token = self.tokens.peek()

    def _match(self, target: str) -> bool:
        tk = self.tokens.peek()
        if tk.kind == 'EOF': return False
        
        # Verificação robusta: confia no lexeme
        if tk.lexeme == target: return True
        
        # Mapeamentos de segurança
        if target == ':' and (tk.kind == 'COLON' or tk.lexeme == ':'): return True
        if target == ';' and (tk.kind == 'SEMI' or tk.lexeme == ';'): return True
        if target == '=' and (tk.kind == 'ASSIGN' or tk.lexeme == '='): return True
        if target == '(' and (tk.kind == 'LPAREN' or tk.lexeme == '('): return True
        if target == ')' and (tk.kind == 'RPAREN' or tk.lexeme == ')'): return True
        if target == '{' and (tk.kind == 'LBRACE' or tk.lexeme == '{'): return True
        if target == '}' and (tk.kind == 'RBRACE' or tk.lexeme == '}'): return True
        if target == ',' and (tk.kind == 'COMMA' or tk.lexeme == ','): return True
        if target == '.' and (tk.kind == 'DOT' or tk.lexeme == '.'): return True
        if target == '[' and (tk.kind == 'LBRACK' or tk.lexeme == '['): return True
        if target == ']' and (tk.kind == 'RBRACK' or tk.lexeme == ']'): return True
        
        return False

    def _consume_if(self, target: str) -> bool:
        if self._match(target):
            self.tokens.next() # Agora garantido que avança!
            return True
        return False

    def parse(self) -> Programa:
        try:
            if self.tokens.accept('KWD', 'program'):
                # Tenta consumir ID se houver
                if self.tokens.peek().kind == 'ID': self.tokens.next()

            declarations = self.decl_topo()
            
            # Se sobrou algo que não é EOF, é erro
            if self.tokens.peek().kind != 'EOF':
                 # Opcional: reportar erro ou ignorar lixo final
                 pass
                 
            return Programa(token=self.start_token, declaracoes=declarations)
        except SyntaxError as e:
            self.error_handler.report_error(e)
            self.synchronize()
            return Programa(token=self.start_token, declaracoes=[])

    def synchronize(self):
        self.tokens.next()
        while self.tokens.peek().kind != 'EOF':
            tk = self.tokens.peek()
            if tk.lexeme in (';', '}'):
                self.tokens.next()
                return
            if tk.kind == 'KWD' and tk.lexeme in ('var', 'if', 'while', 'return', 'class', 'function'):
                return
            self.tokens.next()

    def _is_type(self, token) -> bool:
        # Verifica se é um tipo primitivo ou identificador (para classes)
        return token.kind == 'ID' or token.lexeme in ('int', 'float', 'bool', 'string', 'void', 'dna', 'prot', 'rna', 'any')

    def _expect_type(self) -> str:
        tk = self.tokens.peek()
        if self._is_type(tk):
            self.tokens.next()
            if self._consume_if('['):
                self._consume_if(']')
                return tk.lexeme + "[]"
            return tk.lexeme
        # Se falhar a checagem estrita, mas for ID, aceita
        if tk.kind == 'ID':
            self.tokens.next()
            return tk.lexeme
            
        raise SyntaxError(f"Esperado tipo, chegou '{tk.lexeme}'", tk.line, tk.col)

    def decl_topo(self) -> List[Any]:
        declarations = []
        while self.tokens.peek().kind != 'EOF':
            tk = self.tokens.peek()
            lex = tk.lexeme
            
            if lex == '}': 
                self.tokens.next()
                continue
            
            if lex in ('const', 'var', 'let'): 
                declarations.append(self.decl_var_const())
            elif lex in ('void', 'function', 'def'): 
                declarations.append(self.decl_metodo())
            elif lex == 'class': 
                declarations.append(self.decl_classe())
            else: 
                # Tenta parsear statement solto se não for declaração
                try:
                    declarations.append(self.statement())
                except SyntaxError:
                    # Se falhar, avança para evitar loop infinito em lixo
                    self.tokens.next()
                    
        return declarations

    def decl_var_const(self) -> DeclaracaoVariavel:
        self.tokens.next() # consome var/const
        nome_tk = self.tokens.expect('ID')
        tipo = "any"
        if self._consume_if(':'): tipo = self._expect_type()
        val = None
        if self._consume_if('='): val = self.expression()
        if not self._consume_if(';'): self.tokens.expect('SEMI')
        return DeclaracaoVariavel(token=nome_tk, nome=nome_tk.lexeme, tipo=tipo, valor=val)

    def decl_metodo(self) -> DeclaracaoFuncao:
        start_tk = self.tokens.peek()
        self.tokens.next() # void/function
        
        # Suporte a 'void main' ou 'function main'
        if start_tk.lexeme == 'void' and self.tokens.peek().kind == 'ID':
             pass # void ja consumido
        elif start_tk.lexeme == 'function':
             pass
             
        nome_tk = self.tokens.expect('ID')
        self.tokens.expect('LPAREN') # (
        params_str = []
        if not self._match(')'):
            while True:
                # Pode ser (x: int) ou (int x) ou (x)
                t1 = self.tokens.peek(); self.tokens.next()
                
                # Caso x: int
                if self._consume_if(':'):
                    params_str.append(f"{t1.lexeme}: {self._expect_type()}")
                # Caso int x
                elif self.tokens.peek().kind == 'ID':
                     pname = self.tokens.expect('ID').lexeme
                     params_str.append(f"{pname}: {t1.lexeme}")
                else:
                     params_str.append(f"{t1.lexeme}: any")
                     
                if not self._consume_if(','): break
        
        self.tokens.expect('RPAREN') # )
        
        ret_type = 'void'
        if self._consume_if(':'): ret_type = self._expect_type()
        elif start_tk.lexeme != 'void' and start_tk.lexeme != 'def':
             # Se não definiu retorno explicito e não é void, assume any ou void?
             pass
        
        if start_tk.lexeme == 'void': ret_type = 'void'
             
        return DeclaracaoFuncao(token=start_tk, nome=nome_tk.lexeme, parametros=params_str, corpo=self.bloco_stmt_list(), tipo_retorno=ret_type, is_procedure=(ret_type=='void'))

    def decl_classe(self) -> DeclaracaoClasse:
        tk = self.tokens.expect('KWD', 'class') # Pode falhar se class não for KWD no lexer
        if tk.lexeme != 'class': # Fallback
             pass 
             
        nome_tk = self.tokens.expect('ID')
        self.tokens.expect('LBRACE')
        campos = []
        while not self._match('}') and self.tokens.peek().kind != 'EOF':
            if self.tokens.peek().kind == 'ID':
                fn = self.tokens.expect('ID')
                tp = "any"
                if self._consume_if(':'): tp = self._expect_type()
                self.tokens.expect('SEMI')
                campos.append((fn.lexeme, tp))
            else: self.tokens.next()
        self.tokens.expect('RBRACE')
        return DeclaracaoClasse(token=tk, nome=nome_tk.lexeme, campos=campos)

    def bloco_stmt_list(self) -> List[Any]:
        self.tokens.expect('LBRACE')
        stmts = []
        while not self._match('}') and self.tokens.peek().kind != 'EOF':
            stmts.append(self.statement())
        self.tokens.expect('RBRACE')
        return stmts

    def statement(self) -> Any:
        t = self.tokens.peek()
        lex = t.lexeme
        if lex == 'if': return self.comando_if()
        if lex == 'while': return self.comando_while()
        if lex == 'return': return self.comando_return()
        if lex == 'print': return self.comando_print()
        if lex in ('var', 'let'): return self.decl_var_const()
        if lex == '{': return self.bloco_stmt_list()
        if lex == ';': self.tokens.next(); return InstrucaoExpressao(token=t, expressao=None)
        return self.comando_expr()

    def comando_if(self):
        tk = self.tokens.expect('KWD', 'if') # if
        self.tokens.expect('LPAREN') # (
        cond = self.expression()
        self.tokens.expect('RPAREN') # )
        then_b = self.stmt_or_block_as_list()
        else_b = []
        if self.tokens.accept('KWD', 'else') or (self.tokens.peek().lexeme == 'else' and self.tokens.next()): 
            else_b = self.stmt_or_block_as_list()
        return InstrucaoIf(token=tk, condicao=cond, bloco_if=then_b, bloco_else=else_b)

    def comando_while(self):
        tk = self.tokens.expect('KWD', 'while')
        self.tokens.expect('LPAREN')
        cond = self.expression()
        self.tokens.expect('RPAREN')
        return InstrucaoLoopWhile(token=tk, condicao=cond, corpo=self.stmt_or_block_as_list())

    def stmt_or_block_as_list(self):
        if self._match('{'): return self.bloco_stmt_list()
        return [self.statement()]

    def comando_return(self):
        tk = self.tokens.expect('KWD', 'return')
        expr = None if self._match(';') else self.expression()
        self.tokens.expect('SEMI')
        return InstrucaoRetorno(token=tk, expressao=expr)

    def comando_print(self):
        tk = self.tokens.expect('KWD', 'print')
        self.tokens.expect('LPAREN')
        e = self.expression()
        if self._consume_if(','): self.expression()
        self.tokens.expect('RPAREN'); self.tokens.expect('SEMI')
        return InstrucaoImpressao(token=tk, expressao=e)

    def comando_expr(self):
        e = self.expression()
        self.tokens.expect('SEMI')
        if isinstance(e, InstrucaoAtribuicao): return e
        return InstrucaoExpressao(token=e.token, expressao=e)

    def expression(self): return self.assignment()
    
    def assignment(self):
        l = self.logic_or()
        if self._match('='):
            op = self.tokens.next()
            return InstrucaoAtribuicao(token=op, alvo=l, valor=self.assignment())
        return l

    def logic_or(self):
        l = self.term_soma() 
        while self._match('||') or self._match('&&'): 
            op = self.tokens.next()
            l = ExpressaoBinaria(token=op, esquerda=l, operador=op.lexeme, direita=self.term_soma())
        return l

    def term_soma(self):
        l = self.term_mult()
        while self._match('+') or self._match('-'):
            op = self.tokens.next()
            l = ExpressaoBinaria(token=op, esquerda=l, operador=op.lexeme, direita=self.term_mult())
        return l

    def term_mult(self):
        l = self.unary()
        while self._match('*') or self._match('/') or self._match('%'):
            op = self.tokens.next()
            l = ExpressaoBinaria(token=op, esquerda=l, operador=op.lexeme, direita=self.unary())
        return l

    def unary(self):
        if self._match('-') or self._match('!'):
            op = self.tokens.next()
            return ExpressaoUnaria(token=op, operador=op.lexeme, direita=self.unary())
        return self.primary()

    def primary(self):
        tk = self.tokens.peek()
        
        # Strings e DNA
        if tk.kind == 'STRING' or tk.lexeme.startswith(('"', 'dna"', 'prot"', 'rna"')):
            self.tokens.next()
            val = tk.lexeme.strip('"')
            if tk.lexeme.startswith('dna"'): val = tk.lexeme[4:-1]
            elif tk.lexeme.startswith('prot"'): val = tk.lexeme[5:-1]
            elif tk.lexeme.startswith('rna"'): val = tk.lexeme[4:-1]
            elif tk.lexeme.startswith('"'): val = tk.lexeme[1:-1]
            lit = Literal(token=tk, valor=val)
            if 'dna' in tk.lexeme: lit.tipo_literal = 'dna'
            elif 'prot' in tk.lexeme: lit.tipo_literal = 'prot'
            return lit

        # DNA separado (dna "seq")
        if (tk.kind == 'ID' or tk.kind == 'KWD') and tk.lexeme in ('dna', 'prot', 'rna'):
             possible_type = tk.lexeme
             self.tokens.next()
             if self.tokens.peek().kind == 'STRING':
                 str_tk = self.tokens.next()
                 lit = Literal(token=str_tk, valor=str_tk.lexeme.strip('"'))
                 lit.tipo_literal = possible_type
                 return lit
             return Variavel(token=tk, nome=possible_type)

        if tk.kind in ('DEC_INT', 'FLOAT'):
            self.tokens.next()
            val = float(tk.lexeme) if tk.kind=='FLOAT' else int(tk.lexeme)
            return Literal(token=tk, valor=val)
            
        if tk.lexeme in ('true', 'false'):
            self.tokens.next()
            return Literal(token=tk, valor=(tk.lexeme=='true'))

        if tk.kind == 'ID':
            self.tokens.next()
            if self._consume_if('('):
                args = []
                if not self._match(')'):
                    while True:
                        args.append(self.expression())
                        if not self._consume_if(','): break
                self.tokens.expect('RPAREN')
                return ChamadaFuncao(token=tk, nome=Variavel(token=tk, nome=tk.lexeme), argumentos=args)
            
            expr = Variavel(token=tk, nome=tk.lexeme)
            while True:
                if self._consume_if('['):
                    idx = self.expression()
                    self.tokens.expect('RBRACK')
                    expr = AcessoArray(token=tk, alvo=expr, indice=idx)
                elif self._consume_if('.'):
                    campo = self.tokens.expect('ID').lexeme
                    expr = AcessoCampo(token=tk, alvo=expr, campo=campo)
                else: break
            return expr

        if self._consume_if('('):
            e = self.expression()
            self.tokens.expect('RPAREN')
            return e

        raise SyntaxError(f"Token inesperado: {tk.lexeme}", tk.line, tk.col)