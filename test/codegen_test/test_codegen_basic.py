import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Numero

class TestCodegenBasic(unittest.TestCase):
    def test_numero(self):
        g = CodeGenerator()
        instr = g.visitar(Numero(5))
        self.assertEqual(instr, ["PUSH 5"])