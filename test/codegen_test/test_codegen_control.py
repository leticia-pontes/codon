import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Literal, ExpressaoBinaria, InstrucaoIf

class TestCodegenControl(unittest.TestCase):
    def test_if(self):
        g = CodeGenerator()
        cond = ExpressaoBinaria(Literal(1), '==', Literal(1))
        if_node = InstrucaoIf(cond, [Literal(2)], [], [Literal(3)])

        cod = g.visitar(if_node)

        self.assertTrue(any("JUMP_IF_FALSE" in c for c in cod))

        labels = [c for c in cod if c.startswith("LABEL")]
        self.assertTrue(any("ELSE" in c for c in labels))
        self.assertTrue(any("ENDIF" in c for c in labels))
