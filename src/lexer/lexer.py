# -*- coding: utf-8 -*-
import re
import sys
from collections import namedtuple

# 1. Definição do Token (Tipo e Valor)
Token = namedtuple('Token', ['tipo', 'valor', 'linha', 'coluna'])

# 2. Palavras-Chave e Mapeamento de Tipos
PALAVRAS_CHAVE = {
    "and": "KWD", "or": "KWD", "not": "KWD",
    "if": "KWD", "else": "KWD", "for": "KWD",
    "while": "KWD", "return": "KWD", "break": "KWD",
    "continue": "KWD", "func": "KWD", "var": "KWD",
    "const": "KWD", "import": "KWD", "from": "KWD",
    "as": "KWD", "struct": "KWD", "enum": "KWD",
    "match": "KWD", "case": "KWD", "default": "KWD",
    "true": "KWD", "false": "KWD", "null": "KWD",
    "pub": "KWD", "extern": "KWD", "use": "KWD",
    "int": "KWD", "float": "KWD", "bool": "KWD", 
    "string": "KWD", "dna": "KWD", "rna": "KWD", 
    "prot": "KWD", "void": "KWD"
}

# 3. Definição das Regras Léxicas (Regexes)
REGRAS = [
    # 1. COMENTÁRIOS E ESPAÇOS EM BRANCO (PRIORIDADE MÁXIMA)
    # A regex do comentário de linha foi ajustada para consumir tudo de forma não-gananciosa.
    # A flag re.DOTALL será aplicada na compilação.
    (r'"""([\s\S]*?)"""', None), # BLOCK_COMMENT (O mais longo e não-ganancioso)
    (r'/"(.*?)(\n|$)', None),    # LINE_COMMENT: Começa com /" e consome TUDO até "/.
    (r'//[^\n]*', None),         # LINE_COMMENT: Começa com // e consome TUDO até o fim da linha ou do arquivo.
    (r'[\t\f\r ]+', None),       # WS (Espaços, tabs, etc.)
    (r'\n', None),               # NEWLINE (Apenas para rastrear linha/coluna)

    # 2. TOKENS COMPOSTOS E OPERADORES LONGO
    (r'\.\.\.', 'DOT3'), 
    (r'\.\.', 'DOT2'), 
    (r'->', 'ARROW'), 
    (r'==', 'EQ'),
    (r'!=', 'NE'),
    (r'<=', 'LE'),
    (r'>=', 'GE'),
    (r'\+=', 'PLUS_EQ'),
    (r'-=', 'MINUS_EQ'),
    (r'\*=', 'STAR_EQ'),
    (r'/=', 'SLASH_EQ'),
    (r'%=', 'PERC_EQ'),
    (r'&&', 'AND_AND'),
    (r'\|\|', 'OR_OR'),

    # 3. LITERAIS DE TEXTO (Strings e Literais Biológicos)
    (r'dna"[^"]*"', 'DNA_LIT'),  
    (r'rna"[^"]*"', 'RNA_LIT'),  
    (r'prot"[^"]*"', 'PROT_LIT'),
    (r'"(\\"|[^"])*"', 'STRING'),

    # 4. LITERAIS NUMÉRICOS
    (r'\d+(\.\d+)?([eE][+-]?\d+)', 'FLOAT_EXP'),
    (r'\d+\.\d+', 'FLOAT'),
    (r'\d+', 'DEC_INT'),

    # 5. IDENTIFICADORES E PALAVRAS-CHAVE
    # Permite caracteres ASCII e a maioria dos caracteres UNICODE por padrão
    (r'[a-zA-Z_][a-zA-Z0-9_]*', 'ID'),

    # 6. OPERADORES E DELIMITADORES SIMPLES
    (r'=', 'ASSIGN'),
    (r'\+', 'PLUS'),
    (r'-', 'MINUS'),
    (r'\*', 'STAR'),
    (r'/', 'SLASH'),
    (r'%', 'PERCENT'),
    (r'\^', 'CARET'),
    (r'>', 'GT'),
    (r'<', 'LT'),
    (r'&', 'AMP'),
    (r'\|', 'BAR'),
    
    # Delimitadores
    (r'\(', 'LPAREN'),
    (r'\)', 'RPAREN'),
    (r'\{', 'LBRACE'),
    (r'\}', 'RBRACE'),
    (r';', 'SEMI'),
    (r':', 'COLON'),
    (r',', 'COMMA'),
    (r'\.', 'DOT'),
]

# Compila as regexes com re.UNICODE e re.DOTALL para garantir a leitura correta de caracteres acentuados.
# re.DOTALL (re.S) faz com que '.' case com TUDO, incluindo \n, essencial para BLOCK_COMMENT.
regex_regras = [
    (re.compile(regex, re.UNICODE | re.DOTALL), token_tipo) 
    for regex, token_tipo in REGRAS
]

def analise_lexica(codigo_fonte):
    """
    Realiza a análise léxica do código-fonte e retorna a lista de tokens.
    """
    tokens = []
    linha = 1
    coluna = 1
    pos = 0

    while pos < len(codigo_fonte):
        match = None
        token_tipo = None
        
        # 1. Tenta casar com as regras de tokenização na ordem de prioridade
        for regex, t_tipo in regex_regras:
            m = regex.match(codigo_fonte, pos)
            if m:
                match = m
                token_tipo = t_tipo
                break
        
        if match:
            valor = match.group(0)
            proxima_pos = match.end()
            tamanho_token = len(valor)

            # 2. Tratamento de Elementos Ignorados (Espaços e Comentários)
            if token_tipo is None:
                
                # Conta quebras de linha dentro do token ignorado (WS, NEWLINE, Comentários)
                for char in valor:
                    if char == '\n':
                        linha += 1
                        coluna = 1
                    else:
                        coluna += 1
                
                pos = proxima_pos
                continue

            # 3. Tratamento de Palavras-Chave (Prioridade sobre ID)
            if token_tipo == 'ID':
                if valor in PALAVRAS_CHAVE:
                    token_tipo = PALAVRAS_CHAVE[valor]

            # 4. Adiciona o Token
            tokens.append(Token(token_tipo, valor, linha, coluna))

            # 5. Atualiza a Coluna
            # Incrementa a coluna com o tamanho do token (para o PRÓXIMO token)
            coluna += tamanho_token
            pos = proxima_pos
        
        else:
            # 6. Trata Erro Léxico (Requisito da tarefa)
            caractere_invalido = codigo_fonte[pos]
            print(f"\nERRO LÉXICO: Caractere não reconhecido '{caractere_invalido}' "
                  f"encontrado na Linha {linha}, Coluna {coluna}.")
            
            # Retorna o token de erro e encerra, conforme a exigência de reportar o erro
            # e parar a análise.
            return [Token("LEXICAL_ERROR", caractere_invalido, linha, coluna)]

    return tokens

def imprimir_tabela(tokens):
    """ Imprime a tabela de tokens (valor e tipo). """
    print("\n--- Tabela de Tokens ---")
    print("{:<25} {:<15} {:<6} {:<6}".format("Token", "Tipo", "Lin", "Col"))
    print("-" * 52)
    for token in tokens:
        print(f"{token.valor:<25} {token.tipo:<15} {token.linha:<6} {token.coluna:<6}")
    print("-" * 52)

# 7. Execução Principal
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python lexer.py <arquivo_fonte.cd>")
        sys.exit(1)
    
    caminho_arquivo = sys.argv[1]
    
    try:
        # Garante a leitura do arquivo como UTF-8
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
        sys.exit(1)
    except UnicodeDecodeError:
        print(f"Erro: Falha na decodificação do arquivo. Certifique-se de que '{caminho_arquivo}' está salvo em UTF-8.")
        sys.exit(1)

    lista_tokens = analise_lexica(source_code)

    # Imprime a tabela apenas se a análise não foi interrompida por um erro léxico
    if lista_tokens and lista_tokens[0].tipo != "LEXICAL_ERROR":
        imprimir_tabela(lista_tokens)