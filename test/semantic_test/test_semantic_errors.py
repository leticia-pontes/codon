import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao,
    InstrucaoRetorno, Variavel, Literal, ChamadaFuncao
)
from src.utils.erros import ErrorHandler


class TestSemanticErrors(unittest.TestCase):
    def make_func(self, name, params, corpo, is_proc=False):
        return DeclaracaoFuncao(name, params, corpo, is_proc)

    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # ----------------------------------------------------------
    # Variável não definida
    # ----------------------------------------------------------
    def test_undefined_variable(self):
        # A função deve ser procedure para evitar SEM008
        func = self.make_func(
            "f",
            [],
            [
                InstrucaoRetorno(Variavel("x"))
            ],
            is_proc=True
        )
        eh = self.run_analyzer([func])

        self.assertEqual(len(eh.errors), 1)
        self.assertIn("Uso de variável não definida", eh.errors[0].message)

    # ----------------------------------------------------------
    # Função sem return (funções não-procedure precisam de return) - SEM008
    # ----------------------------------------------------------
    def test_function_missing_return(self):
        func = self.make_func(
            "f",
            ["x"],
            []  # nenhum return
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("requer uma instrução 'return'", eh.errors[0].message)

    # ----------------------------------------------------------
    # Chamada de função não existente - SEM005
    # ----------------------------------------------------------
    def test_call_undefined_function(self):
        f1 = self.make_func(
            "main",
            [],
            [
                # Atribuição (ou Chamada Simples) em vez de InstrucaoRetorno
                InstrucaoAtribuicao(Variavel("res"), "=", ChamadaFuncao(Variavel("foo"), []))
            ],
            is_proc=True
        )
        eh = self.run_analyzer([f1])

        # Espera-se apenas o SEM005
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("função não definida: 'foo'", eh.errors[0].message)

    # ----------------------------------------------------------
    # Número errado de argumentos - SEM009
    # ----------------------------------------------------------
    def test_wrong_argument_count(self):
        f1 = self.make_func(
            "foo",
            ["a", "b"],
            [InstrucaoRetorno(Literal(0))]
        )
        main = self.make_func(
            "main",
            [],
            [
                # Atribuição da chamada com argumento faltando
                InstrucaoAtribuicao(
                    Variavel("res"), "=",
                    ChamadaFuncao(Variavel("foo"), [Literal(1)])  # só 1 argumento
                )
            ],
            is_proc=True
        )
        eh = self.run_analyzer([f1, main])

        # Espera-se apenas o SEM009
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("espera 2 args mas recebeu 1", eh.errors[0].message)