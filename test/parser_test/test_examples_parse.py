import unittest
import os
from src.lexer.analisador_lexico_completo import Lexer, TokenStream
from src.parser.ast.ast_base import Parser, Programa

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'examples')

class ExampleProgramsTest(unittest.TestCase):
    """
    Testa se todos os programas de exemplo em examples/ são válidos
    do ponto de vista sintático (lexer + parser) e imprime tokens.
    """

    def test_all_examples_compile(self):
        success = []
        failed = []

        print(f"📂 Procurando exemplos em: {os.path.abspath(EXAMPLES_DIR)}", flush=True)

        if not os.path.exists(EXAMPLES_DIR):
            self.fail(f"❌ Diretório {EXAMPLES_DIR} não encontrado!")

        for root, _, files in os.walk(EXAMPLES_DIR):
            print(f"\n📁 Entrando em: {root}", flush=True)
            for fname in sorted(files):
                if not fname.endswith(".cd"):
                    continue
                path = os.path.join(root, fname)
                print(f"\n   - {fname}", flush=True)
                print(f"\t🔍 Testando {path} ...", flush=True)

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        codigo = f.read()

                    # --- Lexer + Token Mapping ---
                    lexer = Lexer(codigo)
                    tokens = lexer.tokenize_all()  # lista de tokens
                    # print("\t🟢 Tokens mapeados:")
                    # for t in tokens:
                    #     print(f"\t   {t.linha:>3}:{t.coluna:<3}  {t.tipo:<12}  {t.valor!r}")

                    # --- Parser ---
                    ts = TokenStream(lexer)
                    parser = Parser(ts)
                    ast = parser.parse()

                    self.assertIsInstance(ast, Programa)
                    success.append(path)
                except Exception as e:
                    print(f"\t🔴 ERRO: {str(e)}")
                    failed.append((path, str(e)))

        # ✅ Resumo final
        print("\n" + "=" * 60)
        print("🧬 RESULTADO FINAL DOS TESTES DE EXEMPLOS")
        print("=" * 60)
        print(f"✅ Exemplos analisados com sucesso: {len(success)}")
        print(f"❌ Exemplos com erro de sintaxe: {len(failed)}\n")

        if success:
            print("🟢 SUCESSOS:")
            for path in success:
                print(f"   - {os.path.relpath(path, EXAMPLES_DIR)}")

        if failed:
            print("\n🔴 FALHAS:")
            for path, err in failed:
                print(f"   - {os.path.relpath(path, EXAMPLES_DIR)}")
                print(f"     ↳ Erro: {err}")

        if failed:
            msgs = "\n".join([f"- {p}: {err}" for p, err in failed])
            self.fail(f"\nOs seguintes exemplos falharam na análise sintática:\n{msgs}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
