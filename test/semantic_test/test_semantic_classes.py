import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoClasse, InstrucaoAtribuicao,
    Variavel, Literal, AcessoCampo, DeclaracaoFuncao
)
from src.utils.erros import ErrorHandler, SemanticError


class TestSemanticClasses(unittest.TestCase):
    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    def test_duplicate_field(self):
        cls = DeclaracaoClasse(
            nome="DNA",
            campos=[
                ("seq", "String"),
                ("seq", "String")  # duplicado
            ]
        )

        eh = self.run_analyzer([cls])

        # Verifica se encontrou 1 erro SEM025
        self.assertEqual(len(eh.errors), 1,
            msg=f"Esperado 1 erro (SEM025), mas encontrou {len(eh.errors)}. Erros: {eh.errors}")

        # Verifica a mensagem do erro
        self.assertIsInstance(eh.errors[0], SemanticError)
        self.assertIn("Campo duplicado 'seq' na classe 'DNA'", eh.errors[0].message)


    def test_access_field_of_variable(self):
        cls = DeclaracaoClasse("A", [("x", "Int")])

        # Envolve as instruções em uma função 'main' para o analisador processar
        main_func = DeclaracaoFuncao(
            "main",
            [],
            "void", # Procedure
            [
                InstrucaoAtribuicao(Variavel("a"), "=", Literal(10)), # 'a' se torna Int
                AcessoCampo(Variavel("a"), "x")
            ],
            is_procedure=True
        )

        prog = Programa([cls, main_func])
        eh = self.run_analyzer(prog.declaracoes)

        # Assumindo que o acesso a campo de tipo primitivo ainda não está gerando erro (AttributeError foi corrigido)
        self.assertEqual(len(eh.errors), 0,
            msg=f"Esperado 0 erros, mas encontrou {len(eh.errors)}. Erros: {eh.errors}")