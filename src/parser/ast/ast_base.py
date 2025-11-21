from dataclasses import dataclass
from typing import Optional, List, Tuple, Union
import sys

from src.utils.erros import ErrorHandler, LexicalError, SyntaxError

# Importa as classes do Lexer
try:
    from src.lexer.analisador_lexico_completo import TokenStream, Token
except ImportError:
    print("Erro de Importação do Lexer. Certifique-se de que o path de importação está correto.")
    sys.exit(1)


# ==========================================
# 1. Definição dos Nós da AST
# ==========================================
class ASTNode:
    # Adicionando metadados de linha/coluna para o analisador semântico
    line: int = -1
    col: int = -1

@dataclass
class Programa(ASTNode):
    declaracoes: List[ASTNode]

@dataclass
class DeclaracaoFuncao(ASTNode):
    nome: str
    parametros: List[Tuple[str, str]] # Parâmetros agora são (nome, tipo)
    tipo_retorno: str # Novo campo
    corpo: List[ASTNode]
    is_procedure: bool = False

@dataclass
class DeclaracaoClasse(ASTNode):
    nome: str
    campos: List[Tuple[str, str]]

@dataclass
class InstrucaoIf(ASTNode):
    condicao: ASTNode
    bloco_if: List[ASTNode]
    elif_blocos: List[Tuple[ASTNode, List[ASTNode]]]
    bloco_else: Optional[List[ASTNode]]

@dataclass
class InstrucaoLoopFor(ASTNode):
    inicializacao: ASTNode
    condicao: ASTNode
    passo: ASTNode
    corpo: List[ASTNode]

@dataclass
class InstrucaoLoopWhile(ASTNode):
    condicao: ASTNode
    corpo: List[ASTNode]

@dataclass
class InstrucaoAtribuicao(ASTNode):
    alvo: ASTNode
    operador: str
    valor: ASTNode

@dataclass
class ExpressaoBinaria(ASTNode):
    esquerda: ASTNode
    operador: str
    direita: ASTNode

@dataclass
class ExpressaoUnaria(ASTNode):
    operador: str
    direita: ASTNode

@dataclass
class Literal(ASTNode):
    valor: Union[str, float, int, bool, None] # Adicionado bool e None (null)

@dataclass
class LiteralRange(ASTNode):
    inicio: ASTNode
    fim: ASTNode

@dataclass
class Variavel(ASTNode):
    nome: str

@dataclass
class ChamadaFuncao(ASTNode):
    nome: Union[str, ASTNode]
    argumentos: List[ASTNode]

@dataclass
class AcessoCampo(ASTNode):
    alvo: ASTNode
    campo: str

@dataclass
class AcessoArray(ASTNode):
    alvo: ASTNode
    indice: ASTNode

@dataclass
class InstrucaoRetorno(ASTNode):
    expressao: Optional[ASTNode]

@dataclass
class InstrucaoImpressao(ASTNode):
    expressao: ASTNode

@dataclass
class CriacaoArray(ASTNode):
    tipo: str
    tamanho: ASTNode

@dataclass
class CriacaoClasse(ASTNode):
    classe: str
    argumentos: List[ASTNode]


# ==========================================
# 2. Parser
# ==========================================
class Parser:
    def __init__(self, ts: TokenStream, error_handler=None):
        self.ts = ts
        self.error_handler = error_handler or ErrorHandler()

    def parse(self) -> Programa:
        # ... (Método parse, _skip_to_sync) ...
        declaracoes = []
        while self.ts.peek():
            t = self.ts.peek()
            # print(f"[DEBUG parse] peek={t.tipo if t else None}, valor={t.valor if t else None}")
            try:
                decl = self._declaracao()
                if decl:
                    declaracoes.append(decl)
            except (LexicalError, SyntaxError) as e:
                self.error_handler.report_error(e)
                self.ts.next()
        # print(f"[DEBUG parse] Total de declarações: {len(declaracoes)}")
        return Programa(declaracoes)

    def _skip_to_sync(self):
        while True:
            t = self.ts.peek()
            if t is None or t.tipo in ("SEMI", "RBRACE"):
                self.ts.next() if t else None
                break
            self.ts.next()

    # ==========================================
    # --- Declarações e Instruções ---
    # ==========================================
    def _declaracao(self) -> ASTNode:
        t = self.ts.peek()
        if t and t.tipo == 'KWD':
            if t.valor == 'function' or t.valor == 'procedure' or t.valor == 'void':
                return self._decl_funcao(is_procedure=(t.valor in ('procedure','void')))
            elif t.valor == 'class':
                return self._decl_classe()
        return self._instrucao()

    def _decl_funcao(self, is_procedure: bool) -> DeclaracaoFuncao:
        self.ts.expect("KWD")
        nome_token = self.ts.expect("ID")
        self.ts.expect("LPAREN")

        parametros = []
        if not self.ts.match("RPAREN"):
            # Agora _lista_param retorna a lista de Tuples (nome, tipo)
            parametros = self._lista_param()
            self.ts.expect("RPAREN")

        tipo_retorno = 'void'
        if not is_procedure:
            self.ts.expect("COLON")
            tipo_retorno = self._tipo().valor

        corpo = self._bloco()
        # Passa o tipo de retorno para a AST
        return DeclaracaoFuncao(nome_token.valor, parametros, tipo_retorno, corpo, is_procedure)

    def _decl_classe(self) -> DeclaracaoClasse:
        self.ts.expect("KWD")
        nome_token = self.ts.expect("ID")
        # Suporte opcional a 'extends NomeBase'
        nxt = self.ts.peek()
        if nxt and ((nxt.tipo == 'KWD' and nxt.valor == 'extends') or (nxt.tipo == 'ID' and nxt.valor == 'extends')):
            self.ts.next()  # consome 'extends'
            _ = self.ts.expect("ID")  # nome da superclasse (ignorado nesta AST)
        self.ts.expect("LBRACE")
        campos = []
        while not self.ts.match("RBRACE"):
            campos.append(self._decl_campo())
        return DeclaracaoClasse(nome_token.valor, campos)

    def _decl_campo(self) -> Tuple[str, str]:
        nome = self.ts.expect("ID").valor
        self.ts.expect("COLON")
        tipo = self._tipo().valor
        self.ts.expect("SEMI")
        return (nome, tipo)

    def _tipo(self) -> Optional[Token]:
        # Suporta tipos ID (classes) ou KWD (primitivos)
        tipo_token = self.ts.peek()
        if tipo_token and (tipo_token.tipo == 'KWD' or tipo_token.tipo == 'ID'):
            self.ts.next()
            return tipo_token
        self.error_handler.report_error(
            SyntaxError(f"Esperado tipo, mas encontrou {tipo_token.valor if tipo_token else 'EOF'}",
                        tipo_token.linha if tipo_token else -1,
                        tipo_token.coluna if tipo_token else -1)
        )
        return None

    def _lista_param(self) -> List[Tuple[str, str]]:
        params = []
        while True:
            param_id = self.ts.expect("ID").valor
            self.ts.expect("COLON")
            tipo = self._tipo().valor
            params.append((param_id, tipo)) # Retorna como (nome, tipo)

            if not self.ts.match("COMMA"):
                break
        return params

    def _bloco(self) -> List[ASTNode]:
        self.ts.expect("LBRACE")
        instrucoes = []
        while not self.ts.match("RBRACE"):
            instrucoes.append(self._instrucao())
        return instrucoes

    # ==========================================
    # --- Instruções ---
    # ==========================================
    def _instrucao(self) -> ASTNode:
        t = self.ts.peek()
        if t and t.tipo == 'KWD':
            if t.valor == 'if':
                return self._instrucao_if()
            elif t.valor == 'for':
                return self._instrucao_for()
            elif t.valor == 'while':
                return self._instrucao_while()
            elif t.valor == 'return':
                return self._instrucao_return()
            elif t.valor == 'print':
                return self._instrucao_print()
            elif t.valor in ('var', 'const'):
                return self._decl_var_const()

        # Chamada de função ou atribuição
        return self._instrucao_atribuicao_ou_chamada()

    def _decl_var_const(self) -> Optional[ASTNode]:
        kw = self.ts.expect("KWD")  # 'var' ou 'const'
        # Tenta detectar formato tipado: Tipo (ID/KWD) [ [] ] ... Ident
        var_name_token = None
        t1 = self.ts.peek()
        t2 = self.ts.peek(2)
        if t1 and (t1.tipo in ("KWD","ID")) and t2 and (t2.tipo in ("ID","LBRACK")):
            self.ts.next()  # consome tipo
            # consome pares [] opcionais (ex: int[])
            while self.ts.match("LBRACK"):
                self.ts.expect("RBRACK")
            var_name_token = self.ts.expect("ID")
        else:
            var_name_token = self.ts.expect("ID")
        # Atribuição opcional
        if self.ts.match("ASSIGN"):
            valor = self._expressao()
            self.ts.expect("SEMI")
            return InstrucaoAtribuicao(Variavel(var_name_token.valor), '=', valor)
        else:
            self.ts.expect("SEMI")
            return None

    def _instrucao_atribuicao_ou_chamada(self) -> ASTNode:
        # Usa _exp_primaria_ou_acesso para capturar ID, ID(), ID.campo, ID[indice]
        alvo = self._exp_primaria_ou_acesso()

        atrib_op = self.ts.match("ASSIGN", "ARROW_LEFT", "PLUS_EQ","MINUS_EQ")

        if atrib_op:
            valor = self._expressao()
            self.ts.expect("SEMI")
            return InstrucaoAtribuicao(alvo, atrib_op.valor, valor)

        # Se não é atribuição, deve ser uma expressão que é uma instrução (ex: Chamada de Função, Criação de Classe)
        elif isinstance(alvo, (ChamadaFuncao, CriacaoClasse)):
            self.ts.expect("SEMI")
            return alvo

        else:
            # Se for apenas uma variável ou literal no início de uma instrução, é um erro de sintaxe
            self.ts.expect("SEMI")
            return alvo # Retorna a expressão, será tratada como instrução de descarte se a semântica permitir.

    def _instrucao_if(self) -> InstrucaoIf:
        # Aceita if com ou sem parênteses na condição
        self.ts.expect("KWD")
        if self.ts.match("LPAREN"):
            condicao = self._expressao()
            self.ts.expect("RPAREN")
        else:
            condicao = self._expressao()
        bloco_if = self._bloco()
        elif_blocos = []
        while self.ts.peek() and self.ts.peek().valor == 'elif':
            self.ts.next()
            if self.ts.match("LPAREN"):
                elif_cond = self._expressao()
                self.ts.expect("RPAREN")
            else:
                elif_cond = self._expressao()
            elif_bloco = self._bloco()
            elif_blocos.append((elif_cond, elif_bloco))
        bloco_else = None
        if self.ts.peek() and self.ts.peek().valor == 'else':
            self.ts.next()
            # Suporta 'else if (...) { ... }' como um 'elif' adicional
            if self.ts.peek() and self.ts.peek().valor == 'if':
                self.ts.next()
                self.ts.expect("LPAREN")
                elif_cond = self._expressao()
                self.ts.expect("RPAREN")
                elif_bloco = self._bloco()
                elif_blocos.append((elif_cond, elif_bloco))
            else:
                bloco_else = self._bloco()
        return InstrucaoIf(condicao, bloco_if, elif_blocos, bloco_else)

    def _instrucao_while(self) -> InstrucaoLoopWhile:
        # ... (Método _instrucao_while permanece o mesmo) ...
        self.ts.expect("KWD")
        self.ts.expect("LPAREN")
        condicao = self._expressao()
        self.ts.expect("RPAREN")
        corpo = self._bloco()
        return InstrucaoLoopWhile(condicao, corpo)

    def _instrucao_for(self) -> InstrucaoLoopFor:
        # Suporta variantes com e sem parênteses
        self.ts.expect("KWD")  # 'for'
        has_parens = self.ts.match("LPAREN") is not None

        # Inicialização (consome ';' internamente)
        inicializacao = self._instrucao_atribuicao_ou_chamada()

        condicao = self._expressao()
        self.ts.expect("SEMI")

        # Passo (não consome ';')
        passo = self._atribuicao_ou_chamada_sem_semi()

        if has_parens:
            self.ts.expect("RPAREN")
        corpo = self._bloco()
        return InstrucaoLoopFor(inicializacao, condicao, passo, corpo)

    def _atribuicao_ou_chamada_sem_semi(self) -> ASTNode:
        alvo = self._exp_primaria_ou_acesso()
        atrib_op = self.ts.match("ASSIGN", "ARROW_LEFT", "PLUS_EQ","MINUS_EQ")
        if atrib_op:
            valor = self._expressao()
            return InstrucaoAtribuicao(alvo, atrib_op.valor, valor)
        elif isinstance(alvo, (ChamadaFuncao, CriacaoClasse)):
            return alvo
        else:
            return alvo

    def _instrucao_return(self) -> InstrucaoRetorno:
        # ... (Método _instrucao_return permanece o mesmo) ...
        self.ts.expect("KWD")
        expressao = None
        if not self.ts.match("SEMI"):
            expressao = self._expressao()
            self.ts.expect("SEMI")
        return InstrucaoRetorno(expressao)

    def _instrucao_print(self) -> InstrucaoImpressao:
        # ... (Método _instrucao_print permanece o mesmo) ...
        self.ts.expect("KWD")
        self.ts.expect("LPAREN")
        expr = self._expressao() # Usa _expressao para suportar qualquer tipo de expressão
        # Consome argumentos extras separados por vírgula, ignorando-os na AST simplificada
        while self.ts.match("COMMA"):
            _ = self._expressao()
        self.ts.expect("RPAREN")
        self.ts.expect("SEMI")
        return InstrucaoImpressao(expr)

    # ==========================================
    # --- Expressões ---
    # ==========================================
    def _exp_primaria_ou_acesso(self) -> ASTNode:
        # ... (Método _exp_primaria_ou_acesso permanece o mesmo, é o loop de pós-fixado) ...
        node = self._exp_primaria()

        while True:
            peek = self.ts.peek()
            if not peek: break

            # Chamada de função: sempre é `ID(...)` ou `ID.campo(...)`
            if peek.tipo == 'LPAREN':
                self.ts.next()
                argumentos = []
                while self.ts.peek() and self.ts.peek().tipo != 'RPAREN':
                    arg = self._expressao()
                    argumentos.append(arg)
                    if self.ts.peek() and self.ts.peek().tipo == "COMMA":
                        self.ts.next()
                self.ts.expect("RPAREN")
                node = ChamadaFuncao(node, argumentos)
                continue # Continua o loop para encadear mais acessos

            # Acesso a campo (objeto.campo)
            elif self.ts.match("DOT"):
                campo_token = self.ts.expect("ID")
                node = AcessoCampo(node, campo_token.valor)
                continue

            # Acesso a índice (array[indice])
            elif self.ts.match("LBRACK"):
                indice = self._expressao()
                self.ts.expect("RBRACK")
                node = AcessoArray(node, indice)
                continue

            else:
                break
        return node

    def _exp_primaria(self):
        t = self.ts.peek()
        if not t:
            self.error_handler.report_error(SyntaxError("Esperado expressão, mas EOF", -1, -1))
            return Literal(None)

        try:
            # Literais Simples
            if t.tipo in ("DEC_INT","FLOAT","STRING","CHAR_LIT","DNA_LIT","RNA_LIT","PROT_LIT"):
                self.ts.next()
                if t.tipo=="DEC_INT": return Literal(int(t.valor))
                if t.tipo=="FLOAT": return Literal(float(t.valor))
                if t.tipo=="CHAR_LIT": return Literal(t.valor[1:-1])
                if t.tipo=="STRING": return Literal(t.valor.strip('"'))
                # Lógicas para tipos biológicos
                if t.tipo in ("DNA_LIT","RNA_LIT","PROT_LIT"):
                    # Extrai o valor do literal entre aspas
                    valor = t.valor.split('"',1)[1].rsplit('"',1)[0]
                    return Literal(valor)

            # Expressão Agrupada
            elif t.tipo=="LPAREN":
                self.ts.next()
                expr = self._expressao()
                self.ts.expect("RPAREN")
                return expr

            # ID (Variável)
            elif t.tipo=="ID":
                id_token = self.ts.next()
                return Variavel(id_token.valor)

            # Literais Keyword: true, false, null
            elif t.tipo=="KWD" and t.valor in ("true","false","null"):
                self.ts.next()
                return Literal(True) if t.valor == 'true' else Literal(False) if t.valor == 'false' else Literal(None)

            # Nova Palavra-chave: 'new' para CriacaoClasse ou CriacaoArray
            elif t.tipo=="KWD" and t.valor == 'new':
                self.ts.next()
                # Tipo pode ser ID (classe) ou KWD (primitivo)
                tipo_token = self.ts.peek()
                if not tipo_token or tipo_token.tipo not in ("ID","KWD"):
                    self.ts.expect("ID")
                self.ts.next()
                class_type = tipo_token.valor

                if self.ts.match("LPAREN"):
                    # Criação de Classe: new MinhaClasse(arg1, arg2)
                    argumentos = []
                    while self.ts.peek() and self.ts.peek().tipo != 'RPAREN':
                        arg = self._expressao()
                        argumentos.append(arg)
                        if self.ts.peek() and self.ts.peek().tipo == "COMMA":
                            self.ts.next()
                    self.ts.expect("RPAREN")
                    return CriacaoClasse(class_type, argumentos)

                elif self.ts.match("LBRACK"):
                    # Criação de Array: new int[tamanho]
                    tamanho = self._expressao()
                    self.ts.expect("RBRACK")
                    return CriacaoArray(class_type, tamanho)

            # Range Expression: expr..expr (Usado em For-Each, mas tratado aqui como expressão)
            # NOTA: Range é um operador de baixa precedência, mas como literal é tratado aqui se for literal..literal
            # Se for complexo, a expressão binária tratará. Vamos focar na binária.

            else:
                raise SyntaxError(f"Esperado expressão primária, mas chegou {t.valor}", t.linha, t.coluna)

        except SyntaxError as e:
            self.error_handler.report_error(e)
            self._skip_to_sync()
            return Literal(None)

    # --- Operadores binários e unários ---
    def _expressao(self) -> ASTNode:
        # Adiciona o operador de range '..' (DOT_DOT) antes do OR_OR por convenção de baixa precedência
        return self._exp_range()

    def _exp_range(self):
        node = self._exp_logica_or()
        if self.ts.match("DOT2"):
            direita = self._exp_range() # Associação da direita
            # Se for uma expressão de range, retorna LiteralRange para análise semântica mais fácil
            if isinstance(node, (Literal, Variavel)) and isinstance(direita, (Literal, Variavel)):
                return LiteralRange(node, direita)
            return ExpressaoBinaria(node, "..", direita)
        return node

    def _exp_logica_or(self):
        node = self._exp_logica_and()
        while self.ts.match("OR_OR"):
            op = self.ts.next().valor # consome '||'
            direita = self._exp_logica_and()
            node = ExpressaoBinaria(node, op, direita)
        return node

    def _exp_logica_and(self):
        node = self._exp_relacional()
        while self.ts.match("AND_AND"):
            op = self.ts.next().valor # consome '&&'
            direita = self._exp_relacional()
            node = ExpressaoBinaria(node, op, direita)
        return node

    def _exp_relacional(self):
        node = self._exp_aditiva()
        while True:
            op = self.ts.match("EQ","NE","LT","GT","LE","GE")
            if not op: break
            direita = self._exp_aditiva()
            node = ExpressaoBinaria(node,op.valor,direita)
        return node

    def _exp_aditiva(self):
        node = self._exp_multiplicativa()
        while True:
            op = self.ts.match("PLUS","MINUS")
            if not op: break
            direita = self._exp_multiplicativa()
            node = ExpressaoBinaria(node,op.valor,direita)
        return node

    def _exp_multiplicativa(self):
        node = self._exp_potencia()
        while True:
            op = self.ts.match("STAR","SLASH","PERCENT")
            if not op: break
            direita = self._exp_potencia()
            node = ExpressaoBinaria(node,op.valor,direita)
        return node

    def _exp_potencia(self):
        node = self._exp_unaria()
        if self.ts.match("CARET"):
            direita = self._exp_potencia()
            node = ExpressaoBinaria(node,"^",direita)
        return node

    def _exp_unaria(self):
        op = self.ts.match("PLUS","MINUS","BANG","TILDE")
        if op:
            direita = self._exp_unaria()
            return ExpressaoUnaria(op.valor,direita)
        return self._exp_primaria_ou_acesso()
