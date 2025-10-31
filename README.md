# Codon - Linguagem e Compilador Educacional

[![CI](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml/badge.svg)](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml)

> **Nome provisório:** Codon
> 
> **Objetivo:** linguagem educativa voltada para processamento e análise de dados biológicos (DNA/RNA/proteínas) com builtins científicos prontos e uma sintaxe simples para estudantes e pesquisadores.


## Sumário

- [Visão Geral](#visão-geral)
- [Fluxo do Compilador](#fluxo-do-compilador)
- [Léxico / Tokens](#léxico--tokens)
- [Sintaxe / Gramática (essencial)](#sintaxe--gramática-essencial)
- [Ambiente / Env e Interpreter](#ambiente--env-e-interpreter)
- [Biblioteca Biológica Embutida](#biblioteca-biológica-embutida)
- [Exemplos](#exemplos)
- [Instalação e Uso](#instalação-e-uso)
  - [Linux / macOS (bash)](#linux--macos-bash)
  - [Windows (PowerShell)](#windows-powershell)
- [Executar Testes (localmente)](#executar-testes-localmente)
  - [Bash (Linux/macOS)](#bash-linuxmacos)
  - [PowerShell (Windows)](#powershell-windows)
  - [Executar somente pytest](#executar-somente-pytest)
- [CI - GitHub Actions](#ci---github-actions)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Como Contribuir](#como-contribuir)
- [Licença](#licença)


## Visão Geral

O objetivo do **Codon** é fornecer uma linguagem simples e expressiva para tarefas comuns em bioinformática educacional: manipulação de sequências, cálculos biológicos, transformações e scripts experimentais. A linguagem é interpretada - o compilador fornece lexer, parser, AST e interpretador (executor) com um ambiente (`Env`) contendo funções nativas.

### Fluxo (resumo)
```
fonte (.ar) ──► Lexer (tokens) ──► Parser (AST) ──► Interpreter (execução)
└─► Env (escopos)
````

## Léxico / Tokens

O lexer converte texto em tokens (`NUMBER`, `STRING`, `IDENT`, `LET`, `IF`, `PLUS`, etc.). Espaços e comentários são ignorados; strings suportam escapes; números podem ser inteiros, decimais e notação científica.

Token produzido: `Token(kind, lexeme, literal, line, col)` e a lista termina com `EOF`.


## Sintaxe (trecho essencial - EBNF)

```ebnf
program := { declaration }

declaration := varDecl | statement
	
	varDecl := 'let' IDENT '=' expression ';'
	
	statement := printStmt | ifStmt | whileStmt | exprStmt | block
		
		printStmt := 'print' expression ';'
		
		ifStmt := 'if' '(' expression ')' statement [ 'else' statement ]
		
		whileStmt := 'while' '(' expression ')' statement
		
		exprStmt := expression ';'
		
		block := '{' { declaration } '}'

expression := assignment
	
	assignment := IDENT '=' assignment | logic_or
		
		logic_or := logic_and { '||' logic_and }
			
		logic_and := equality { '&&' equality }
			
		equality := comparison { ( '==' | '!=' ) comparison }
			
		comparison := term { ( '>' | '>=' | '<' | '<=' ) term }
			
		term := factor { ( '+' | '-' ) factor }
			
		factor := unary { ( '*' | '/' | '%' ) unary }
			
		unary := ( '!' | '-' ) unary | call
			
		call := primary { '(' [ arguments ] ')' }
			
		arguments := expression { ',' expression }

primary := NUMBER | STRING | 'true' | 'false' | IDENT | '(' expression ')'
````


## Ambiente (Env) e Interpreter

* `Env` é uma cadeia de dicionários encadeados (`parent`) que armazena variáveis e funções nativas.
* `define(name, value)` cria/atualiza no escopo atual.
* `get(name)` busca recursivamente.
* `assign(name, value)` atualiza onde foi declarada (caso contrário erro).
* Blocos `{ ... }` criam um `Env` filho permitindo sombrear variáveis.

O interpretador implementa `eval(expr, env)` e `exec(stmt, env)`.


## Biblioteca Biológica Embutida (builtins principais)

Algumas funções a serem implementadas em `globals`:

* `dna_gc(seq) -> float`
* `dna_comp(seq) -> string`
* `dna_revcomp(seq) -> string`
* `dna_transcribe(seq) -> string`
* `dna_back_transcribe(seq) -> string`
* `dna_translate(seq) -> string`
* `seq_hamming(a, b) -> int`
* `seq_kmer_count(seq, k) -> dict`
* `seq_motif_find(seq, motif) -> [int]`
* `mm_rate(vmax, s, km) -> float`
* `hill(x, k, n) -> float`
* `logistic(t, K, r, N0) -> float`
* `bio_and(a,b)`, `bio_or(a,b)`, `bio_not(a)`

> Todas as funções aceitam entradas em strings/números e fazem normalização interna.


## Exemplos

**Transcrição simples**

```codon
function transcrever(DNA) {
  RNA = ""
  for i = 0; i < length(DNA); i = i + 1 {
    if DNA[i] == 'A' {
      RNA = RNA + "U"
    } else if DNA[i] == 'T' {
      RNA = RNA + "A"
    } else if DNA[i] == 'C' {
      RNA = RNA + "G"
    } else if DNA[i] == 'G' {
      RNA = RNA + "C"
    }
  }
  return RNA
}

s = "ATCG"
print(transcrever(s))
```


## Instalação e Uso

> Python ≥ 3.10 instalado.

### Linux / macOS (bash)

```bash
# 1. clone o repositório e entre na pasta do repositório
git clone https://github.com/leticia-pontes/codon.git
cd codon

# 2. criar e ativar virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 3. instalar dependências
pip install -r requirements.txt || true

# 4. rodar um programa (sem instalar o pacote)
PYTHONPATH=./ python -m src.compilador run examples/basicos/hello_world.dg

# 5. rodar testes
./scripts/run_all_tests.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/leticia-pontes/codon.git
cd codon

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt

# executar exemplo
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python -m src.compilador run examples\basicos\hello_world.dg

# rodar testes via script PS
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

## Executar Testes (rápido)

### Bash (Linux / macOS)

```bash
# se virtualenv ativo:
pytest test -q

# ou usar script:
./scripts/run_all_tests.sh
```

### PowerShell (Windows)

```powershell
# ativar .venv
.\.venv\Scripts\Activate.ps1
pytest test -q

# ou usar script:
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

### Executar somente PyTest

```bash
pytest test -q
```

## CI - GitHub Actions

Este repositório inclui um workflow que roda automaticamente testes em `push` e `pull_request` para a branch `main` (Ubuntu + Windows). Veja `.github/workflows/ci.yml`.

## Estrutura do Projeto (resumo)

```
compilador/
├── README.md
├── requirements.txt
├── src/
│   ├── compilador.py    # entrypoint
│   ├── lexer/
│   ├── parser/
│   ├── runtime/
│   └── utils/
├── docs/
├── examples/
├── test/
└── scripts/
```


## Como Contribuir

1. Fork → branch com seu recurso/bugfix → PR targeting `main`.
2. Escreva testes que cubram seu código.
3. Mantenha o estilo do projeto e atualize `docs/` quando necessário.


## Observação

Não estamos abertos a contribuições no momento (somente dos membros do grupo, claro).
