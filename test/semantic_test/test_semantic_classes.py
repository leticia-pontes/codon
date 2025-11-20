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
            # Tipos corrigidos para minúsculo
            campos=[
                ("seq", "string"), 
                ("seq", "string")  # duplicado
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
        # Tipo corrigido para 'int'
        cls = DeclaracaoClasse("A", [("x", "int")])

        main_func = DeclaracaoFuncao(
            "main",
            [],
            "void", # Tipo de retorno
            [
                InstrucaoAtribuicao(Variavel("a"), "=", Literal(10)), # 'a' se torna 'int'
                AcessoCampo(Variavel("a"), "x") # Tenta acessar 'x' em 'a' (int)
            ],
            is_procedure=True
        )

        prog = Programa([cls, main_func])
        eh = self.run_analyzer(prog.declaracoes)

        # CORREÇÃO: Deve falhar com SEM026, pois 'a' é um int e não uma classe.
        self.assertEqual(len(eh.errors), 1,
            msg=f"Esperado 1 erro (SEM026) ao acessar campo de tipo primitivo. Erros: {eh.errors}")
        self.assertIsInstance(eh.errors[0], SemanticError)
        self.assertIn("Acesso a campo ('x') de tipo inválido ou indefinido: 'int'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM026")