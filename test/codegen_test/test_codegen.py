import unittest
from src.codegen.gerador_codigo import CodeGenerator
from src.parser.ast.ast_base import Programa, DeclaracaoFuncao, Literal, Variavel, InstrucaoAtribuicao, ExpressaoBinaria, InstrucaoRetorno

class TestCodegen(unittest.TestCase):
    def test_funcao_simples(self):
        func = DeclaracaoFuncao(
            nome="main",
            parametros=[],
            corpo=[InstrucaoRetorno(Literal(5))],
            is_procedure=False
        )
        prog = Programa([func])
        cg = CodeGenerator()
        code = cg.generate(prog)

        self.assertEqual(code[0], ["CALL", "main", 0])
        self.assertEqual(code[1], ["HALT"])

        self.assertIn(["LABEL", "FUNC_main"], code)
        self.assertIn(["PUSH", 5], code)
        self.assertIn(["RETURN"], code)

    def test_atribuicao_variavel(self):
        atribuicao = InstrucaoAtribuicao(Variavel("x"), "=", Literal(10))
        func = DeclaracaoFuncao("main", [], [atribuicao], False)
        prog = Programa([func])

        cg = CodeGenerator()
        code = cg.generate(prog)

        self.assertIn(["PUSH", 10], code)
        self.assertIn(["STORE", "x"], code)

    def test_expressao_binaria(self):
        expr = ExpressaoBinaria(Literal(2), "+", Literal(3))
        func = DeclaracaoFuncao("main", [], [InstrucaoRetorno(expr)], False)
        prog = Programa([func])

        cg = CodeGenerator()
        code = cg.generate(prog)

        self.assertIn(["PUSH", 2], code)
        self.assertIn(["PUSH", 3], code)
        self.assertTrue(
            ["ADD"] in code or ["BINOP", "+"] in code
        )

if __name__ == '__main__':
    unittest.main()
