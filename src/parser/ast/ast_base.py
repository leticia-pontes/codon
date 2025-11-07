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
    pass

@dataclass
class Programa(ASTNode):
    declaracoes: List[ASTNode]

@dataclass
class DeclaracaoFuncao(ASTNode):
    nome: str
    parametros: List[str]
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
    valor: Union[str, float, int]

@dataclass
class LiteralRange(ASTNode):
    inicio: ASTNode
    fim: ASTNode

@dataclass
class Variavel(ASTNode):
    nome: str

@dataclass
class ChamadaFuncao(ASTNode):
    nome: str
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
# 2. Classe Parser
# ==========================================
class Parser:
    def __init__(self, ts: TokenStream, error_handler=None):
        self.ts = ts
        self.error_handler = error_handler or ErrorHandler()

    def parse(self) -> Programa:
        declaracoes = []
        while self.ts.peek():
            try:
                declaracoes.append(self._declaracao())
            except (LexicalError, SyntaxError) as e:
                self.error_handler.report_error(e)
                # Consume token problemático para não travar
                self.ts.next()
        return Programa(declaracoes)

    def _skip_to_sync(self):
        # Função para tentar sincronizar após um erro e continuar parsing
        while True:
            t = self.ts.peek()
            if t is None or t.tipo in ("SEMI", "RBRACE"):
                self.ts.next() if t else None
                break
            self.ts.next()

    def _declaracao(self) -> ASTNode:
        t = self.ts.peek()
        if t and t.tipo == 'KWD':
            if t.valor == 'function':
                return self._decl_funcao(is_procedure=False)
            elif t.valor == 'procedure':
                return self._decl_funcao(is_procedure=True)
            elif t.valor == 'class':
                return self._decl_classe()
        return self._instrucao()

    # --- Declarações ---
    def _decl_funcao(self, is_procedure: bool) -> DeclaracaoFuncao:
        self.ts.expect("KWD")
        nome_token = self.ts.expect("ID")
        self.ts.expect("LPAREN")

        parametros = []
        if not self.ts.match("RPAREN"):
            parametros_com_tipo = self._lista_param(com_tipo=True)
            self.ts.expect("RPAREN")
            parametros = [p.split(":")[0].strip() for p in parametros_com_tipo]

        if not is_procedure:
            self.ts.expect("COLON")
            self._tipo()

        corpo = self._bloco()
        return DeclaracaoFuncao(nome_token.valor, parametros, corpo, is_procedure)

    def _decl_classe(self) -> DeclaracaoClasse:
        self.ts.expect("KWD")
        nome_token = self.ts.expect("ID")
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
        tipo_token = self.ts.peek()
        if tipo_token and (tipo_token.tipo == 'KWD' or tipo_token.tipo == 'ID'):
            return self.ts.next()
        self.error_handler.report_error(
            SyntaxError(f"Esperado tipo, mas encontrou {tipo_token.valor if tipo_token else 'EOF'}",
                        tipo_token.linha if tipo_token else -1,
                        tipo_token.coluna if tipo_token else -1)
        )
        return None

    def _lista_param(self, com_tipo: bool = False) -> List[str]:
        params = []
        while True:
            param_id = self.ts.expect("ID").valor
            if com_tipo and self.ts.peek() and self.ts.peek().tipo == "COLON":
                self.ts.next()
                tipo = self._tipo().valor
                params.append(f"{param_id}: {tipo}")
            else:
                params.append(param_id)
            if not self.ts.match("COMMA"):
                break
        return params

    def _bloco(self) -> List[ASTNode]:
        self.ts.expect("LBRACE")
        instrucoes = []
        while not self.ts.match("RBRACE"):
            instrucoes.append(self._instrucao())
        return instrucoes

    # --- Instruções ---
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
                self.ts.next()
                id_token = self.ts.expect("ID")
                self.ts.expect("ASSIGN")
                valor = self._expressao()
                self.ts.expect("SEMI")
                return InstrucaoAtribuicao(Variavel(id_token.valor), '=', valor)
        return self._instrucao_atribuicao_ou_chamada()

    def _instrucao_atribuicao_ou_chamada(self) -> ASTNode:
        alvo = self._exp_primaria_ou_acesso()
        atrib_op = self.ts.match("ASSIGN","PLUS_EQ","MINUS_EQ")
        if atrib_op:
            valor = self._expressao()
            self.ts.expect("SEMI")
            return InstrucaoAtribuicao(alvo, atrib_op.valor, valor)
        self.ts.expect("SEMI")
        return alvo

    def _instrucao_if(self) -> InstrucaoIf:
        self.ts.expect("KWD")
        self.ts.expect("LPAREN")
        condicao = self._expressao()
        self.ts.expect("RPAREN")
        bloco_if = self._bloco()
        elif_blocos = []
        while self.ts.peek() and self.ts.peek().valor == 'elif':
            self.ts.next()
            self.ts.expect("LPAREN")
            elif_cond = self._expressao()
            self.ts.expect("RPAREN")
            elif_bloco = self._bloco()
            elif_blocos.append((elif_cond, elif_bloco))
        bloco_else = None
        if self.ts.peek() and self.ts.peek().valor == 'else':
            self.ts.next()
            bloco_else = self._bloco()
        return InstrucaoIf(condicao, bloco_if, elif_blocos, bloco_else)

    def _instrucao_while(self) -> InstrucaoLoopWhile:
        self.ts.expect("KWD")
        self.ts.expect("LPAREN")
        condicao = self._expressao()
        self.ts.expect("RPAREN")
        corpo = self._bloco()
        return InstrucaoLoopWhile(condicao, corpo)

    def _instrucao_for(self) -> InstrucaoLoopFor:
        self.ts.expect("KWD")
        init_alvo = self._exp_primaria_ou_acesso()
        init_op = self.ts.expect("ASSIGN").valor
        init_valor = self._expressao()
        inicializacao = InstrucaoAtribuicao(init_alvo, init_op, init_valor)
        self.ts.expect("SEMI")
        condicao = self._expressao()
        self.ts.expect("SEMI")
        passo_alvo = self._exp_primaria_ou_acesso()
        passo_op_token = self.ts.match("ASSIGN","PLUS_EQ","MINUS_EQ","PLUS","MINUS")
        passo_valor = Literal(1) if passo_op_token.valor in ("PLUS","MINUS") else self._expressao()
        passo = InstrucaoAtribuicao(passo_alvo, passo_op_token.valor, passo_valor)
        corpo = self._bloco()
        return InstrucaoLoopFor(inicializacao, condicao, passo, corpo)

    def _instrucao_return(self) -> InstrucaoRetorno:
        self.ts.expect("KWD")
        expressao = None
        if not self.ts.match("SEMI"):
            expressao = self._expressao()
            self.ts.expect("SEMI")
        return InstrucaoRetorno(expressao)

    def _instrucao_print(self) -> InstrucaoImpressao:
        self.ts.expect("KWD")
        self.ts.expect("LPAREN")
        expr = self._expressao()
        self.ts.expect("RPAREN")
        self.ts.expect("SEMI")
        return InstrucaoImpressao(expr)

    # ==========================================
    # --- Expressões ---
    # ==========================================
    def _exp_primaria_ou_acesso(self) -> ASTNode:
        t = self.ts.peek()

        # 1️⃣ Criação de array: new Tipo[expr]
        if t.tipo == "ID" and t.valor == "new":
            self.ts.next()  # consome 'new'
            tipo_token = self.ts.expect("KWD") or self.ts.expect("ID")
            self.ts.expect("LBRACK")
            tamanho_expr = self._expressao()
            self.ts.expect("RBRACK")
            return CriacaoArray(tipo_token.valor, tamanho_expr)

        # 2️⃣ Variável, literal ou parêntese
        node = self._exp_primaria()

        # 3️⃣ Chamada de função ou construtor de classe, acesso a campos ou arrays
        while True:
            if self.ts.peek() and self.ts.peek().tipo == 'LPAREN':
                self.ts.next()
                argumentos = []
                while self.ts.peek() and self.ts.peek().tipo != 'RPAREN':
                    argumentos.append(self._expressao())
                    self.ts.match("COMMA")
                self.ts.expect("RPAREN")
                if isinstance(node, Variavel):
                    # Construtor de classe ou função
                    node = CriacaoClasse(node.nome, argumentos)
                else:
                    node = ChamadaFuncao(node, argumentos)
            elif self.ts.match("DOT"):
                campo_token = self.ts.expect("ID")
                node = AcessoCampo(node, campo_token.valor)
            elif self.ts.match("LBRACK"):
                indice = self._expressao()
                self.ts.expect("RBRACK")
                node = AcessoArray(node, indice)
            else:
                break
        return node

    def _exp_primaria(self):
        t = self.ts.peek()
        if not t:
            self.error_handler.report_error(SyntaxError("Esperado expressão, mas EOF", -1, -1))
            return Literal(None)
        try:
            if t.tipo in ("DEC_INT","FLOAT","STRING","CHAR_LIT","DNA_LIT","RNA_LIT","PROT_LIT"):
                self.ts.next()
                if t.tipo=="DEC_INT": return Literal(int(t.valor))
                if t.tipo=="FLOAT": return Literal(float(t.valor))
                if t.tipo=="CHAR_LIT": return Literal(t.valor[1:-1])
                if t.tipo=="STRING": return Literal(t.valor.strip('"'))
                if t.tipo in ("DNA_LIT","RNA_LIT","PROT_LIT"):
                    valor = t.valor.split('"',1)[1].rsplit('"',1)[0]
                    return Literal(valor)
            elif t.tipo=="LPAREN":
                self.ts.next()
                expr=self._expressao()
                self.ts.expect("RPAREN")
                return expr
            elif t.tipo=="ID":
                id_token=self.ts.next()
                return Variavel(id_token.valor)
            elif t.tipo=="KWD" and t.valor in ("true","false","null"):
                self.ts.next()
                return Literal(t.valor)
            else:
                raise SyntaxError(f"Esperado expressão primária, mas chegou {t.valor}", t.linha, t.coluna)
        except SyntaxError as e:
            self.error_handler.report_error(e)
            self._skip_to_sync()
            return Literal(None)

    # --- Operadores binários e unários ---
    def _expressao(self) -> ASTNode:
        return self._exp_logica_or()

    def _exp_logica_or(self):
        node = self._exp_logica_and()
        while self.ts.match("OR_OR"):
            direita = self._exp_logica_and()
            node = ExpressaoBinaria(node,"||",direita)
        return node

    def _exp_logica_and(self):
        node = self._exp_relacional()
        while self.ts.match("AND_AND"):
            direita = self._exp_relacional()
            node = ExpressaoBinaria(node,"&&",direita)
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
        return self._exp_primaria()
