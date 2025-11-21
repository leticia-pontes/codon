import unittest
import os
from src.lexer.analisador_lexico_completo import Lexer, TokenStream
from src.parser.ast.ast_base import Parser, Programa
from src.utils.erros import ErrorHandler, LexicalError

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')

EXPECTED_ERRORS = {
    "sample_error.cd": LexicalError
}

class ExampleProgramsTest(unittest.TestCase):
    """
    Testa se todos os programas de exemplo em examples/ são válidos
    do ponto de vista sintático (lexer + parser) e imprime tokens.
    """

    def test_all_examples_compile(self):
        success = []
        failed = []

        print(f"[INFO]  Procurando exemplos em: {os.path.abspath(EXAMPLES_DIR)}", flush=True)

        if not os.path.exists(EXAMPLES_DIR):
            self.fail(f"[INFO] Diretório {EXAMPLES_DIR} não encontrado!")

        for root, _, files in os.walk(EXAMPLES_DIR):
            print(f"\n[INFO] Entrando em: {root}", flush=True)
            for fname in sorted(files):
                if not fname.endswith(".cd"):
                    continue
                path = os.path.join(root, fname)
                print(f"\n   - {fname}", flush=True)
                print(f"\t[INFO] Testando {path} ...", flush=True)

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        codigo = f.read()

                    # --- Lexer ---
                    error_handler = ErrorHandler()                # Cria apenas 1 handler
                    lexer = Lexer(codigo, error_handler=error_handler)
                    tokens = lexer.tokenize_all()                 # Gera tokens

                    # --- Parser ---
                    ts = TokenStream(lexer)
                    parser = Parser(ts, error_handler=error_handler)  # Mesma instância
                    ast = parser.parse()

                    if 'sample_error.cd' in fname:
                        self.assertTrue(parser.error_handler.has_errors())
                        types = [type(e).__name__ for e in parser.error_handler.errors]
                        self.assertIn("LexicalError", types)

                    else:
                        # Arquivo válido deve passar
                        self.assertIsInstance(ast, Programa)
                        self.assertFalse(parser.error_handler.has_errors(), msg=f"{fname} não deve gerar erros")
                        success.append(path)

                except Exception as e:
                    # Aqui só imprimimos tokens quando houve erro
                    print("\t[INFO] Tokens antes do erro:")
                    for t in tokens:
                        print(f"\t   {t.linha:>3}:{t.coluna:<3}  {t.tipo:<12}  {t.valor!r}")

                    # Checar se o erro era esperado (você pode definir uma lista de erros esperados por arquivo)
                    erro_esperado = EXPECTED_ERRORS.get(fname)  # dict: {nome_arquivo: tipo_erro_esperado}
                    if erro_esperado and isinstance(e, erro_esperado):
                        print(f"\t[INFO] ERRO esperado: {type(e).__name__}")
                        success.append(path)
                    else:
                        print(f"\t[INFO] ERRO inesperado: {str(e)}")
                        failed.append((path, str(e)))

        # Resumo final
        print("\n" + "=" * 60)
        print("[INFO] RESULTADO FINAL DOS TESTES DE EXEMPLOS")
        print("=" * 60)
        print(f"[INFO] Exemplos analisados com sucesso: {len(success)}")
        print(f"[INFO] Exemplos com erro de sintaxe: {len(failed)}\n")

        if success:
            print("[INFO] SUCESSOS:")
            for path in success:
                print(f"   - {os.path.relpath(path, EXAMPLES_DIR)}")

        if failed:
            print("\n[INFO] FALHAS:")
            for path, err in failed:
                print(f"   - {os.path.relpath(path, EXAMPLES_DIR)}")
                print(f"     ↳ Erro: {err}")

        if failed:
            msgs = "\n".join([f"- {p}: {err}" for p, err in failed])
            self.fail(f"\nOs seguintes exemplos falharam na análise sintática:\n{msgs}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
