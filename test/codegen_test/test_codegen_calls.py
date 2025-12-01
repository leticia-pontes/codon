import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Numero, ChamadaFuncao

class TestCodegenCalls(unittest.TestCase):
    def test_call(self):
        g = CodeGenerator()
        call = ChamadaFuncao("print", [Numero(9)])
        cod = g.visitar(call)
        self.assertEqual(cod, ["PUSH 9", "CALL print 1"])