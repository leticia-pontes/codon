import unittest
from src.semantic.analyzer import SemanticAnalyzer
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao,
    InstrucaoIf, InstrucaoRetorno, InstrucaoLoopWhile, Variavel, Literal,
    ExpressaoBinaria, ExpressaoUnaria
)
from src.utils.erros import ErrorHandler, SemanticError


class TestSemanticTypes(unittest.TestCase):

    def run_analyzer(self, decls):
        eh = ErrorHandler()
        an = SemanticAnalyzer(error_handler=eh)
        an.analyze(Programa(decls))
        return eh

    # Função auxiliar corrigida: usa is_procedure
    def make_func(self, nome, corpo, is_proc=False):
        tipo_retorno = "void" if is_proc else "int"
        # O campo correto na AST é 'is_procedure'
        return DeclaracaoFuncao(nome, [], tipo_retorno, corpo, is_procedure=is_proc)

    # ----------------------------------------------------------
    # 1. Checagem de Tipo em Expressão Binária (SEM010)
    # ----------------------------------------------------------

    def test_invalid_arithmetic_operation(self):
        """Testa 'int + string' (invalido) deve gerar SEM010."""
        func = self.make_func(
            "calc",
            [
                # z <- 10 + "texto"
                InstrucaoAtribuicao(
                    Variavel("z"), "<-",
                    ExpressaoBinaria(Literal(10), "+", Literal("texto"))
                ),
                InstrucaoRetorno(Literal(0)) # Adicionado return para isolar SEM010
            ]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        # CORREÇÃO: Alterar a asserção para corresponder à mensagem real
        self.assertIn("Tipos incompatíveis", eh.errors[0].message) 
        self.assertEqual(eh.errors[0].code, "SEM010")

    def test_valid_arithmetic_operation(self):
        """Testa 'int + float' (valido) deve passar sem erros."""
        func = self.make_func(
            "calc",
            [
                # z <- 10 + 3.14
                InstrucaoAtribuicao(
                    Variavel("z"), "<-",
                    ExpressaoBinaria(Literal(10), "+", Literal(3.14))
                ),
                InstrucaoRetorno(Literal(0)) # Adicionado return para evitar SEM008
            ]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 0)

    # ----------------------------------------------------------
    # 2. Checagem de Tipo em Condições (SEM018)
    # ----------------------------------------------------------

    def test_if_condition_not_boolean(self):
        """Testa if(10) (int) deve gerar SEM018."""
        func = self.make_func(
            "main",
            [
                InstrucaoIf(
                    condicao=Literal(10), # Condição não-booleana
                    bloco_if=[],
                    elif_blocos=[], # Argumento posicional faltante na AST
                    bloco_else=None # Argumento posicional faltante na AST
                )
            ],
            is_proc=True
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("A condição da instrução 'if' deve ser do tipo 'bool'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM018")

    def test_while_condition_not_boolean(self):
        """Testa while("texto") (string) deve gerar SEM018."""
        func = self.make_func(
            "main",
            [
                InstrucaoLoopWhile(
                    condicao=Literal("loop"), # Condição não-booleana
                    corpo=[]
                )
            ],
            is_proc=True
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("A condição do loop 'while' deve ser do tipo 'bool'", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM018")

    # ----------------------------------------------------------
    # 3. Checagem de Tipo de Retorno (SEM012 - Incompatível)
    # ----------------------------------------------------------

    def test_return_type_mismatch(self):
        """Testa função que deve retornar int mas retorna string (SEM012)."""
        func = DeclaracaoFuncao(
            nome="getInt",
            parametros=[],
            tipo_retorno="int",
            corpo=[
                InstrucaoRetorno(Literal("nao sou int")) # Retorna string
            ]
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("O tipo de retorno da função 'getInt' é incompatível", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM012")

    # ----------------------------------------------------------
    # 4. Checagem de Tipo de Retorno (SEM013 - Valor em procedure)
    # ----------------------------------------------------------

    def test_return_value_in_procedure(self):
        """Testa procedure que retorna valor (SEM013)."""
        func = self.make_func(
            "p",
            [
                InstrucaoRetorno(Literal(10)) # Retorno com valor em procedure
            ],
            is_proc=True
        )
        eh = self.run_analyzer([func])
        self.assertEqual(len(eh.errors), 1)
        self.assertIn("Uma procedure não pode retornar um valor", eh.errors[0].message)
        self.assertEqual(eh.errors[0].code, "SEM013")


if __name__ == '__main__':
    unittest.main()