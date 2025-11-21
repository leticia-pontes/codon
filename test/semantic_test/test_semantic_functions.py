import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao,
    InstrucaoRetorno, Variavel, Literal, ChamadaFuncao
)
# Adicionar SemanticError para uso em assertions (boa prática)
from src.utils.erros import ErrorHandler, SemanticError


class TestSemanticFunctions(unittest.TestCase):
    # Ajudante para rodar o analisador
    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # ----------------------------------------------------------
    # Função sem return (não-procedure) - SEM008
    # ----------------------------------------------------------
    def test_function_missing_return(self):
        f = DeclaracaoFuncao(
            nome="f",
            parametros=[],
            tipo_retorno="int", # CORREÇÃO: Adicionar tipo_retorno (assume 'int' se não é procedure)
            corpo=[],
            is_procedure=False
        )

        prog = Programa([f])
        eh = self.run_analyzer(prog.declaracoes)

        self.assertEqual(len(eh.errors), 1)
        self.assertIn("requer uma instrução 'return'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM008") # CORREÇÃO: Checar código de erro

    # ----------------------------------------------------------
    # Chamada com número errado de argumentos - SEM009
    # ----------------------------------------------------------
    def test_function_call_wrong_arity(self):
        # A aridade de 'f' é 2 (a, b)
        f = DeclaracaoFuncao("f", [("a", "int"), ("b", "int")], "int", [InstrucaoRetorno(Literal(1))])

        # Colocamos a chamada em uma função procedure para isolar o SEM009
        main = DeclaracaoFuncao(
            "main",
            [],
            "void", # CORREÇÃO: Adicionar tipo_retorno
            [InstrucaoAtribuicao(Variavel("x"), "<-", ChamadaFuncao(Variavel("f"), [Literal(1)]))], # Só 1 argumento
            is_procedure=True
        )

        prog = Programa([f, main])
        eh = self.run_analyzer(prog.declaracoes)

        self.assertEqual(len(eh.errors), 1)
        self.assertIn("espera 2 args mas recebeu 1", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM009") # CORREÇÃO: Checar código de erro

    # ----------------------------------------------------------
    # Chamada de função não definida - SEM005
    # ----------------------------------------------------------
    def test_call_undefined_function(self):
        # Colocamos a chamada em uma função procedure para isolar o SEM005
        call = DeclaracaoFuncao(
            "main",
            [],
            "void", # CORREÇÃO: Adicionar tipo_retorno
            [InstrucaoAtribuicao(Variavel("x"), "<-", ChamadaFuncao(Variavel("g"), []))],
            is_procedure=True
        )

        prog = Programa([call])
        eh = self.run_analyzer(prog.declaracoes)

        self.assertEqual(len(eh.errors), 1)
        # Removido `.lower()` desnecessário
        self.assertIn("função não definida: 'g'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM005") # CORREÇÃO: Checar código de erro