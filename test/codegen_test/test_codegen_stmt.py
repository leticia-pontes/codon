import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Literal, InstrucaoAtribuicao, Variavel

class TestCodegenStmt(unittest.TestCase):
    def test_atribuicao(self):
        g = CodeGenerator()
        stmt = InstrucaoAtribuicao(Variavel("x"), "=", Literal(7))
        cod = g.visitar(stmt)
        self.assertEqual(cod, ["PUSH 7", "STORE x"])