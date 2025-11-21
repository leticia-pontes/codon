import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, InstrucaoAtribuicao, Variavel, Literal,
    ExpressaoBinaria
)
from src.utils.erros import ErrorHandler

class TestSemanticVariables(unittest.TestCase):
    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # ----------------------------------------------------------
    # Variável não definida - SEM003
    # ----------------------------------------------------------
    def test_undefined_variable(self):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)

        # x <- y   (y não declarada)
        prog = Programa([
            InstrucaoAtribuicao(
                alvo=Variavel("x"),
                operador="<-",
                valor=Variavel("y")
            )
        ])

        an.analyze(prog)

        self.assertEqual(len(eh.errors), 1)
        self.assertIn("Uso de variável não definida: 'y'", eh.errors[0].message)

    # ----------------------------------------------------------
    # Variável declarada por atribuição (Válido)
    # ----------------------------------------------------------
    def test_declared_on_first_assignment(self):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)

        # x <- 1    (declara x)
        # y <- x    (usa x)
        prog = Programa([
            InstrucaoAtribuicao(Variavel("x"), "<-", Literal(1)),
            InstrucaoAtribuicao(Variavel("y"), "<-", Variavel("x")),
        ])

        an.analyze(prog)

        # nenhum erro
        self.assertEqual(len(eh.errors), 0)

    # ----------------------------------------------------------
    # Variável não definida em expressão binária - SEM003
    # ----------------------------------------------------------
    def test_binary_expression_uses_vars(self):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)

        # z <- x + 2    (x não existe)
        prog = Programa([
            InstrucaoAtribuicao(
                Variavel("z"), "<-",
                ExpressaoBinaria(
                    esquerda=Variavel("x"),
                    operador="+",
                    direita=Literal(2)
                )
            )
        ])

        an.analyze(prog)

        self.assertEqual(len(eh.errors), 1)
        self.assertIn("Uso de variável não definida: 'x'", eh.errors[0].message)