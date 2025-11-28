import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Numero, ExpressaoBinaria

class TestCodegenExpr(unittest.TestCase):
    def test_soma(self):
        g = CodeGenerator()
        expr = ExpressaoBinaria(Numero(2), '+', Numero(3))
        codigo = g.visitar(expr)
        self.assertEqual(codigo, ["PUSH 2", "PUSH 3", "ADD"])

    def test_sub(self):
        g = CodeGenerator()
        expr = ExpressaoBinaria(Numero(10), '-', Numero(4))
        codigo = g.visitar(expr)
        self.assertEqual(codigo, ["PUSH 10", "PUSH 4", "SUB"])
