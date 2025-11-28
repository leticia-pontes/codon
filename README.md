# Codon - Linguagem e Compilador Educacional

[![CI](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml/badge.svg)](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml)

> **Nome provisório:** Codon
>
> **Objetivo:** Linguagem educativa para processamento e análise de dados biológicos (DNA, RNA, proteínas), com builtins científicos prontos e sintaxe simples para estudantes e pesquisadores.

---

## Sumário

* [Visão Geral](#visão-geral)

  * [Fluxo do Compilador](#fluxo-do-compilador)
* [Léxico / Tokens](#léxico--tokens)
* [Sintaxe / Gramática (implementada)](#sintaxe--gramática-implementada)
* [Ambiente / Env e Interpreter](#ambiente--env-e-interpreter)
* [Biblioteca Biológica Embutida](#biblioteca-biológica-embutida)
* [Exemplos](#exemplos)
* [Instalação e Uso](#instalação-e-uso)

  * [Linux / macOS (bash)](#linux--macos-bash)
  * [Windows (PowerShell)](#windows-powershell)
* [Executar Testes (localmente)](#executar-testes-localmente)

  * [Bash (Linux/macOS)](#bash-linuxmacos)
  * [PowerShell (Windows)](#powershell-windows)
* [CI - GitHub Actions](#ci---github-actions)
* [Estrutura do Projeto](#estrutura-do-projeto)
* [Como Contribuir](#como-contribuir)
* [Licença](#licença)

---

## Visão Geral

O **Codon** oferece uma linguagem simples e expressiva para tarefas comuns em bioinformática educacional: manipulação de sequências, cálculos biológicos, transformações e scripts experimentais.

A linguagem é interpretada: o compilador fornece **lexer, parser, AST** e **interpretador (executor)** com um ambiente (`Env`) que contém funções nativas.

### Fluxo do Compilador (resumo)

```
fonte (.cd) ──► Lexer (tokens) ──► Parser (AST) ──► Interpreter (execução)
└─► Env (escopos e variáveis)
```

---

## Léxico / Tokens

O lexer converte texto em tokens (`NUMBER`, `STRING`, `IDENT`, `LET`, `IF`, `PLUS`, etc.).

* Espaços e comentários são ignorados.
* Strings suportam escapes (`\n`, `\t`, etc.).
* Números suportam inteiros, decimais e notação científica.

Exemplo de token:

```text
Token(kind, lexeme, literal, line, col)
```

A lista termina sempre com `EOF`.

---

## Sintaxe / Gramática (implementada)

Abaixo está a gramática **exatamente como implementada no parser atual**, incluindo suporte a funções, chamadas, blocos, declarações e expressões completas.

```ebnf
declaration   := funDecl | varDecl | statement

funDecl       := 'function' IDENT '(' parameters? ')' block
parameters    := IDENT ( ',' IDENT )*

varDecl       := 'let' IDENT ( '=' expression )? ';'

statement     := exprStmt | printStmt | ifStmt | whileStmt | forStmt | returnStmt | block

exprStmt      := expression ';'
printStmt     := 'print' expression ';'
returnStmt    := 'return' expression? ';'

ifStmt        := 'if' '(' expression ')' statement ( 'else' statement )?
whileStmt     := 'while' '(' expression ')' statement
forStmt       := 'for' IDENT '=' expression ';' expression ';' expression block

block         := '{' declaration* '}'

expression    := assignment
assignment    := IDENT '=' assignment | logic_or

logic_or      := logic_and ( '||' logic_and )*
logic_and     := equality ( '&&' equality )*

equality      := comparison ( ( '==' | '!=' ) comparison )*
comparison    := term ( ( '>' | '>=' | '<' | '<=' ) term )*
term          := factor ( ( '+' | '-' ) factor )*
factor        := unary  ( ( '*' | '/' | '%' ) unary )*

unary         := ( '!' | '-' ) unary | call

call          := primary ( '(' arguments? ')' )*
arguments     := expression ( ',' expression )*

primary       := NUMBER | STRING | 'true' | 'false' | IDENT | '(' expression ')'
```

---

## Ambiente (Env) e Interpreter

* `Env` é uma **cadeia de dicionários encadeados** (`parent`) que armazena variáveis e funções nativas.
* `define(name, value)` cria ou atualiza no escopo atual.
* `get(name)` busca recursivamente em escopos pai.
* `assign(name, value)` atualiza onde a variável foi declarada (erro se não existir).
* Blocos `{ ... }` criam **Env filho**, permitindo sombrear variáveis.

O interpretador implementa:

```python
eval(expr, env)  # avalia expressões
exec(stmt, env)  # executa declarações
```

---

## Biblioteca Biológica Embutida (builtins principais)

Funções nativas que operam em strings/números e realizam **normalização interna**:

* DNA/RNA:

  * `dna_gc(seq) -> float`
  * `dna_comp(seq) -> string`
  * `dna_revcomp(seq) -> string`
  * `dna_transcribe(seq) -> string`
  * `dna_back_transcribe(seq) -> string`
  * `dna_translate(seq) -> string`

* Sequência:

  * `seq_hamming(a, b) -> int`
  * `seq_kmer_count(seq, k) -> dict`
  * `seq_motif_find(seq, motif) -> [int]`

* Modelos matemáticos:

  * `mm_rate(vmax, s, km) -> float`
  * `hill(x, k, n) -> float`
  * `logistic(t, K, r, N0) -> float`

* Operadores booleanos biológicos:

  * `bio_and(a,b)`, `bio_or(a,b)`, `bio_not(a)`

---

## Exemplos

**Transcrição simples de DNA → RNA**

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

---

## Instalação e Uso

> Requer **Python ≥ 3.10**.

### Linux / macOS (bash)

```bash
git clone https://github.com/leticia-pontes/codon.git
cd codon

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt || true

PYTHONPATH=./ python -m src.compilador run examples/basicos/hello_world.cd

./scripts/run_all_tests.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/leticia-pontes/codon.git
cd codon

python -m venv .venv
.\.venv\Scripts\activate

pip install -r requirements.txt

$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
python -m src.compilador run examples\basicos\hello_world.cd

Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

---

## Executar Testes (rápido)

### Bash (Linux/macOS)

```bash
python -m unittest discover -s test -p "*.py" -v
./scripts/run_all_tests.sh
```

### PowerShell (Windows)

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s test -p "*.py" -v

Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

---

## CI - GitHub Actions

O workflow roda testes automaticamente em push/pull_request na branch `main`.

---

## Estrutura do Projeto

```
codon/
├── docs/
├── examples/
│   ├── avancados/
│   ├── basicos/
│   ├── intermediarios/
├── scripts/
├── src/
│   ├── codegen/
│   ├── lexer/
│   ├── parser/
│   ├── semantic/
│   ├── utils/
│   └── compilador.py
├── test/
│   ├── lexer_test/
│   └── parser_test/
├── tools/
└── README.md
```

---

## Como Contribuir

1. Fork → branch → PR.
2. Inclua testes.
3. Atualize `docs/` quando necessário.

> Contribuições restritas ao grupo no momento.
