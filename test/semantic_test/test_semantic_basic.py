import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao,
    InstrucaoRetorno, Variavel, Literal, ExpressaoBinaria,
    AcessoArray, ChamadaFuncao
)
from src.utils.erros import ErrorHandler, SemanticError


class TestSemanticBasic(unittest.TestCase):
    # Ajudante corrigido: Usando is_procedure
    def make_func(self, name, params, return_type, corpo, is_proc=False):
        params_typed = [(p, 'int') for p in params]
        # CORREÇÃO: Usar is_procedure=is_proc
        return DeclaracaoFuncao(name, params_typed, return_type, corpo, is_procedure=is_proc)

    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # -----------------------------------------------------------
    # Testa função simples com return (válido)
    # -----------------------------------------------------------
    def test_valid_function_with_return(self):
        func = self.make_func(
            "f",
            ["x"],
            "int", # Tipo de retorno corrigido para 'int'
            [
                InstrucaoRetorno(
                    ExpressaoBinaria(
                        Variavel("x"),
                        "+",
                        Literal(1)
                    )
                )
            ]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 0, msg=f"Esperado 0 erros. Erros: {eh.errors}")

    # -----------------------------------------------------------
    # Testa uso correto de variável declarada por atribuição
    # -----------------------------------------------------------
    def test_assignment_declares_variable(self):
        func = self.make_func(
            "g",
            [],
            "int", # Tipo de retorno corrigido para 'int'
            [
                InstrucaoAtribuicao(Variavel("a"), "=", Literal(10)),
                InstrucaoAtribuicao(
                    Variavel("b"), "=",
                    ExpressaoBinaria(Variavel("a"), "+", Literal(1))
                ),
                InstrucaoRetorno(Variavel("b"))
            ]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 0, msg=f"Esperado 0 erros. Erros: {eh.errors}")

    # -----------------------------------------------------------
    # Testa função sem parâmetros, apenas return
    # -----------------------------------------------------------
    def test_function_no_params(self):
        func = self.make_func(
            "h",
            [],
            "int", # Tipo de retorno corrigido para 'int'
            [InstrucaoRetorno(Literal(42))]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 0, msg=f"Esperado 0 erros. Erros: {eh.errors}")