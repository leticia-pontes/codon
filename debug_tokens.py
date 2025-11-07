from src.lexer.analisador_lexico_completo import Lexer
import src.lexer.analisador_lexico_completo as lex
# print(f"REGRAS\n{lex.REGRAS}\n")
# print(f"COMPILED REGRAS\n{lex._compiled_rules}\n")

codigo = r'''
/" Define a concentração padrão e o fator de diluição "/

const MAX_CONC = 1.0^(-8);   // Literal Float c/ separador e exp
var fator_diluicao = 1.0;    // Variável mutável

// Estrutura de tipo de dados que simula um vetor (apenas o nome do tipo)
var int[] volume_mastermix;

// Função principal de inicialização
void inicializar_placa(num_amostras: int) {
    // Declaração local
    var int i = 0;

    // Atribuição básica
    volume_mastermix = new int[num_amostras + 5];

    // Loop simples (uso de KWD 'while', Operador de comparação)
    while i < num_amostras {
        volume_mastermix[i] = 20; // 20µL por poço
        i += 1; // Operador composto
    }
}

// Chamada de método (chamada implícita, sem return)
inicializar_placa(100);
'''

lx = Lexer(codigo)

try:
    toks = lx.tokenize_all()
    for t in toks:
        print(f"{t.linha:>3}:{t.coluna:<3}  {t.tipo:<12}  {t.valor!r}")
except Exception as e:
    print("Erro léxico:", e)
