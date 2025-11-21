import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao,
    InstrucaoRetorno, Variavel, Literal, ChamadaFuncao
)
from src.utils.erros import ErrorHandler, SemanticError


class TestSemanticErrors(unittest.TestCase):
    def make_func(self, name, params, return_type, corpo, is_proc=False):
        params_typed = [(p, 'int') for p in params]
        return DeclaracaoFuncao(name, params_typed, return_type, corpo, is_procedure=is_proc)

    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # ----------------------------------------------------------
    # Variável não definida (SEM003) e Retorno em Procedure (SEM013)
    # ----------------------------------------------------------
    def test_undefined_variable_and_procedure_return_value(self):
        func = self.make_func(
            "f",
            [],
            "void", # Tipo de retorno
            [
                InstrucaoRetorno(Variavel("x"))
            ],
            is_proc=True
        )
        eh = self.run_analyzer([func])

        self.assertEqual(len(eh.errors), 2,
                         msg=f"Esperado 2 erros (SEM003, SEM013). Encontrado {len(eh.errors)}. Erros: {eh.errors}")

        error_codes = {e.code for e in eh.errors}
        self.assertIn("SEM003", error_codes)
        self.assertIn("SEM013", error_codes)

    # ----------------------------------------------------------
    # Função sem return (funções não-procedure precisam de return) - SEM008
    # ----------------------------------------------------------
    def test_function_missing_return(self):
        func = self.make_func(
            "f",
            ["x"],
            "int", # Tipo de retorno forçando função a retornar
            [] # nenhum return
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("requer uma instrução 'return'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM008")

    # ----------------------------------------------------------
    # Chamada de função não existente - SEM005
    # ----------------------------------------------------------
    def test_call_undefined_function(self):
        f1 = self.make_func(
            "main",
            [],
            "void",
            [
                InstrucaoAtribuicao(Variavel("res"), "=", ChamadaFuncao(Variavel("foo"), []))
            ],
            is_proc=True
        )
        eh = self.run_analyzer([f1])

        # Espera-se apenas o SEM005
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("função não definida: 'foo'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM005")

    # ----------------------------------------------------------
    # Número errado de argumentos - SEM009
    # ----------------------------------------------------------
    def test_wrong_argument_count(self):
        f1 = self.make_func(
            "foo",
            ["a", "b"],
            "int",
            [InstrucaoRetorno(Literal(0))]
        )
        main = self.make_func(
            "main",
            [],
            "void",
            [
                InstrucaoAtribuicao(
                    Variavel("res"), "=",
                    ChamadaFuncao(Variavel("foo"), [Literal(1)]) # só 1 argumento, espera 2
                )
            ],
            is_proc=True
        )
        eh = self.run_analyzer([f1, main])

        # Espera-se apenas o SEM009
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("espera 2 args mas recebeu 1", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM009")