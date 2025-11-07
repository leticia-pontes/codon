import unittest
import sys
import os

# Ajusta o caminho de importação para encontrar os módulos em src/
# Isso é crucial para que o teste consiga importar o Lexer e o Parser.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Importa as classes necessárias
try:
    from src.lexer.analisador_lexico_completo import Lexer, TokenStream
    from src.parser.ast.ast_base import (
        Parser,
        Programa,
        DeclaracaoFuncao,
        DeclaracaoClasse,
        InstrucaoIf,
        InstrucaoLoopWhile,
        AcessoArray,
        InstrucaoAtribuicao,
        ExpressaoBinaria,
        InstrucaoImpressao
    )
except ImportError as e:
    print(f"Erro de importação: {e}")
    print("Certifique-se de que os arquivos Lexer e Parser estão nos locais esperados (src/lexer e src/parser).")
    sys.exit(1)


class ParserAcceptanceTest(unittest.TestCase):
    """
    Testes de aceitação para o Parser, verificando se ele consegue processar
    diferentes estruturas gramaticais e construir os nós da AST corretamente.
    """

    def test_full_program_structure(self):
        """
        Testa um programa completo, verificando a criação de:
        - Declaração de Função (com tipo de retorno)
        - Instrução While
        - Acesso a Array (DNA[i])
        - Declaração de Classe (com campos terminados em SEMI)
        - Atribuição (usando <-)
        - Chamada de função (print)
        """

        codigo_fonte = r"""
function transcrever(DNA: Dbase): Rbase {
    RNA <- "";
    i = 0;
    while(i < length(DNA)){
        if (DNA[i] == 'A'){
            RNA += "U";
        }
        i = i + 1;
    }
    return RNA;
}

class Nucleotideo {
    base: Nbase;
    posicao: int;
}
sequence <- dna"ATCGTACG";
print(transcrever(sequence));
"""
        # 1. Análise Léxica
        lexer = Lexer(codigo_fonte)
        token_stream = TokenStream(lexer)

        # 2. Análise Sintática
        parser = Parser(token_stream)

        # O teste é bem-sucedido se a função parse() não levantar uma exceção
        try:
            ast = parser.parse()
        except Exception as e:
            self.fail(f"Parsing falhou inesperadamente: {e}")

        # 3. Verificação da AST de Nível Superior

        self.assertIsInstance(ast, Programa, "O resultado do parse deve ser um objeto Programa.")
        self.assertEqual(len(ast.declaracoes), 4, "Esperado 4 declarações/instruções de nível superior.")

        # Declaração 1: function transcrever
        decl1 = ast.declaracoes[0]
        self.assertIsInstance(decl1, DeclaracaoFuncao, "A primeira declaração deve ser uma função.")
        self.assertEqual(decl1.nome, "transcrever")
        self.assertFalse(decl1.is_procedure)

        # Verificando a presença do while loop dentro da função
        while_node = next((instr for instr in decl1.corpo if isinstance(instr, InstrucaoLoopWhile)), None)
        self.assertIsNotNone(while_node, "O nó InstrucaoLoopWhile não foi encontrado no corpo da função.")

        # Verificando o acesso a array DNA[i] dentro do while/if
        if_node = next((instr for instr in while_node.corpo if isinstance(instr, InstrucaoIf)), None)
        self.assertIsNotNone(if_node, "O nó InstrucaoIf não foi encontrado dentro do loop while.")

        # A condição do if é uma ExpressaoBinaria, e a esquerda dela deve ser o AcessoArray
        self.assertIsInstance(if_node.condicao, ExpressaoBinaria, "A condição do if deve ser uma ExpressaoBinaria.")
        self.assertEqual(if_node.condicao.operador, '==', "O operador relacional/biológico deve ser '=='")

        # O lado esquerdo da seta é a comparação `DNA[i] == 'A'`
        self.assertIsInstance(if_node.condicao.esquerda, AcessoArray, "O lado esquerdo da comparação deve ser um acesso de array.")
        self.assertEqual(if_node.condicao.esquerda.alvo.nome, 'DNA', "O acesso a array deve ser feito na variável DNA.")
        self.assertEqual(if_node.condicao.esquerda.indice.nome, 'i', "O índice do acesso a array deve ser a variável i.")

        # Declaração 2: class Nucleotideo
        decl2 = ast.declaracoes[1]
        self.assertIsInstance(decl2, DeclaracaoClasse, "A segunda declaração deve ser uma classe.")
        self.assertEqual(decl2.nome, "Nucleotideo")
        self.assertEqual(len(decl2.campos), 2, "A classe deve ter 2 campos.")

        # Declaração 3: sequence <- dna"..."
        decl3 = ast.declaracoes[2]
        self.assertIsInstance(decl3, InstrucaoAtribuicao, "A terceira instrução deve ser uma atribuição.")
        self.assertEqual(decl3.operador, '<-')

        # Declaração 4: print(...)
        decl4 = ast.declaracoes[3]
        self.assertIsInstance(decl4, InstrucaoImpressao, "A quarta instrução deve ser uma impressão.")


if __name__ == '__main__':
    # Este é o comando para executar apenas este arquivo de teste
    unittest.main(argv=['first-arg-is-ignored'], exit=False)