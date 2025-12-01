# Resumo Técnico - Compilador Codon

## Informações do Projeto

- **Nome:** Compilador Codon
- **Repositório:** https://github.com/leticia-pontes/codon
- **Linguagem de Implementação:** Python 3.10+
- **Target:** LLVM IR
- **Execução:** JIT via llvmlite

---

## Cumprimento dos Requisitos da Disciplina

### ✅ 1. Manual de Utilização

**Arquivo:** [`MANUAL_UTILIZACAO.md`](MANUAL_UTILIZACAO.md)

**Conteúdo:**
- Comandos do compilador (`codon run`, `codon build`)
- Estrutura de programas
- **Tipos de dados:** int, double, bool, string, void, arrays, structs, classes, enums, maps
- **Operadores:** aritméticos, comparação, lógicos, bitwise, incremento/decremento
- **Estruturas de controle:** if/else, while, for, for-each, break, continue
- **Funções:** declaração, parâmetros, retorno, recursão
- **Arrays:** declaração, acesso, métodos (push, pop, length), slicing
- **Strings:** concatenação, acesso, comparação, iteração
- **Structs:** definição, instanciação, acesso a campos
- **Classes:** definição, construtor, herança, métodos, `this`, `super`
- **Enums:** definição e uso
- **Generics:** funções, classes e structs genéricas com parâmetros de tipo
- **Maps:** dicionários chave-valor com suporte a múltiplos tipos
- **Funções nativas:** print, input, strlen, sqrt, pow, conversões
- **10+ exemplos completos** de código

---

### ✅ 2. Manual de Instalação para Leigo

**Arquivo:** [`MANUAL_INSTALACAO.md`](MANUAL_INSTALACAO.md)

**Conteúdo:**
- **Pré-requisitos:** Instalação do Python (com screenshots conceituais)
- **Instalação passo a passo:**
  - Windows (PowerShell)
  - Linux (Ubuntu/Debian)
  - macOS (via Homebrew)
- **Script automático:** `install.bat` (Windows) e `install.sh` (Linux/macOS)
- **Verificação:** Como testar se instalou corretamente
- **Primeiro programa:** Criar e executar um Hello World
- **Solução de problemas:** 8 problemas comuns e suas soluções
- **Desinstalação:** Como remover o compilador

**Features do instalador:**
- Verifica Python instalado
- Cria ambiente virtual automaticamente
- Instala dependências (llvmlite)
- Configura comando `codon` global
- Permite executar `codon run <arquivo>` de qualquer diretório

---

### ✅ 3. Analisador Léxico (Lexer)

**Implementação:** `src/lexer/analisador_lexico_completo.py`

**Funcionalidades:**
- **Tokens identificados:**
  - Palavras-chave: `function`, `procedure`, `let`, `if`, `else`, `while`, `for`, `return`, `class`, `struct`, `enum`, `new`, `this`, `super`, etc.
  - Literais: números (int, double), strings (com escapes), booleanos
  - Identificadores
  - Operadores: aritméticos, comparação, lógicos, bitwise, atribuição
  - Delimitadores: `{}`, `()`, `[]`, `;`, `,`, `.`
  - Comentários: `//` (linha) e `/* */` (bloco)

- **TokenStream:** Buffer de tokens com `peek()`, `next()`, `push_back()`, `expect()`
- **Tratamento de erros:** Posição (linha, coluna) de erros léxicos
- **Testes:** `test/lexer_test/` (3 arquivos de teste)

---

### ✅ 4. Analisador Sintático (Parser - AST)

**Implementação:** 
- Parser: `src/parser/ast/ast_base.py`
- AST nodes: `src/parser/ast/declaracoes.py`, `src/parser/ast/expressoes.py`

**Gramática implementada:**
- **Declarações:** funções, variáveis, classes, structs, enums
- **Instruções:** if/else, while, for, for-each, return, break, continue, blocos
- **Expressões:** 
  - Aritméticas: `+`, `-`, `*`, `/`, `%`, `**`
  - Relacionais: `==`, `!=`, `<`, `<=`, `>`, `>=`
  - Lógicas: `&&`, `||`, `!`
  - Bitwise: `&`, `|`, `^`, `~`, `<<`, `>>`
  - Atribuição: `=`, `+=`, `-=`, `*=`, `/=`
  - Acesso: arrays `[]`, structs/classes `.`, chamadas `()`
  - Unárias: `-`, `!`, `++`, `--`
  - Ternária: `? :`

- **Construções especiais:**
  - Generics: `<T, U>` em funções, classes e structs
  - Maps: `map<K, V>`
  - Array slicing: `arr[start:end]`
  - For-each: `for item in collection`

- **Gramática formal:** `docs/gramatica-formal-atualizada.md` (EBNF completa)
- **Testes:** `test/parser_test/` (2 arquivos, testa 47 exemplos)

**Técnica:** Recursive Descent Parser com lookahead

---

### ✅ 5. Analisador Semântico

**Implementação:**
- Analyzer: `src/semantic/analyzer.py`
- Tabela de símbolos: `src/semantic/tabela_simbolos.py`
- Verificador de tipos: `src/semantic/verificador_tipos.py`

**Verificações:**
- **Escopos:** Gerenciamento de escopos aninhados (funções, blocos, classes)
- **Declaração de variáveis:** Verifica se variável foi declarada antes do uso
- **Tipos:** 
  - Compatibilidade de tipos em atribuições
  - Tipos de operandos em expressões
  - Tipos de retorno de funções
  - Tipos de parâmetros em chamadas
- **Classes:**
  - Herança válida
  - Acesso a membros (`this`, `super`)
  - Construtores
- **Generics:** Resolução de tipos genéricos e instanciação
- **Funções:** Número e tipo de argumentos em chamadas

- **Mensagens de erro:** Indica linha, coluna e descrição do erro semântico
- **Testes:** `test/semantic_test/` (7 arquivos, ~30 testes)

---

### ✅ 6. Gerador de Código (LLVM IR)

**Implementação:**
- Codegen: `src/codegen/llvm_codegen.py`
- Otimizador: `src/codegen/otimizador.py`

**Geração de código para:**
- **Tipos primitivos:** int (i32), double, bool (i1), string (i8*)
- **Funções:** Declaração, parâmetros, retorno, chamadas
- **Variáveis:** Alocação (alloca), load, store
- **Operadores:** Todos os aritméticos, relacionais, lógicos, bitwise
- **Controle de fluxo:** if/else (br, phi), while (loop), for
- **Arrays:** 
  - Alocação dinâmica (malloc)
  - Acesso indexado (GEP)
  - Métodos: push, pop, length
  - Slicing com cópia
- **Strings:**
  - Literais como constantes globais
  - Concatenação (malloc + memcpy)
  - Comparação (strcmp)
  - strlen
- **Structs:** 
  - Tipos nomeados (`%StructName`)
  - GEP para acessar campos
  - Alocação com malloc
- **Classes:**
  - Struct com vtable implícita
  - Construtores
  - Herança (cópia de campos da classe pai)
  - Métodos com `this`
- **Enums:** Mapeamento para i32
- **Generics:** 
  - **Monomorphization:** Instanciação concreta para cada tipo usado
  - Funções genéricas: `func_T1_T2`
  - Classes genéricas: `Class_T1`
- **Maps:**
  - Struct com arrays de chaves e valores
  - Suporte a int, string, bool, double, classes (via `equals`)
  - set, get, size

**Funções nativas (printf, malloc, etc.):**
- Declaradas como external functions
- printf, strlen, strcmp, sqrt, pow
- malloc, free (para alocação dinâmica)

**Otimizações:**
- Constant folding básico
- Dead code elimination (opcional)

**Execução:**
- JIT via llvmlite.binding
- Chama função `main()` automaticamente

**Testes:** `test/codegen_test/` (7 arquivos, testa operações, controle, chamadas, etc.)

---

## Estrutura de Diretórios

```
codon/
├── MANUAL_UTILIZACAO.md        ← Manual completo da linguagem
├── MANUAL_INSTALACAO.md        ← Guia para leigos
├── QUICK_START.md              ← Guia rápido
├── README.md                   ← Visão geral e entrega
├── install.bat                 ← Instalador Windows
├── install.sh                  ← Instalador Linux/macOS
├── setup.py                    ← Configuração pip
├── codon.py                    ← CLI legado
├── codon/
│   └── __init__.py             ← CLI moderno (comando global)
├── src/
│   ├── compilador.py           ← Pipeline principal
│   ├── lexer/
│   │   ├── analisador_lexico_completo.py  ← Lexer
│   │   ├── tokens.py
│   │   └── afds/
│   ├── parser/
│   │   ├── parser.py
│   │   └── ast/
│   │       ├── ast_base.py     ← Parser recursivo
│   │       ├── declaracoes.py  ← AST nodes
│   │       └── expressoes.py
│   ├── semantic/
│   │   ├── analyzer.py         ← Análise semântica
│   │   ├── tabela_simbolos.py
│   │   └── verificador_tipos.py
│   └── codegen/
│       ├── llvm_codegen.py     ← Gerador LLVM IR
│       └── otimizador.py
├── docs/
│   ├── gramatica-formal-atualizada.md  ← Gramática EBNF
│   ├── especificacao-linguagem.md
│   └── arquitetura.md
├── examples/
│   ├── basicos/                ← 24 exemplos básicos
│   ├── intermediarios/         ← 17 exemplos intermediários
│   └── avancados/              ← 6 exemplos avançados
├── test/
│   ├── lexer_test/             ← 3 arquivos
│   ├── parser_test/            ← 2 arquivos
│   ├── semantic_test/          ← 7 arquivos
│   └── codegen_test/           ← 7 arquivos
└── scripts/
    ├── run_all_tests.ps1       ← Testes Windows
    └── run_all_tests.sh        ← Testes Linux/macOS
```

---

## Como Avaliar

### 1. Instalação

```bash
git clone https://github.com/leticia-pontes/codon.git
cd codon

# Windows
.\install.bat

# Linux/macOS
./install.sh
```

Ative o venv e teste:
```bash
codon run examples/basicos/hello_world.cd
```

### 2. Executar Testes

```bash
# Windows
.\scripts\run_all_tests.ps1

# Linux/macOS
./scripts/run_all_tests.sh
```

Deve passar **14 testes unitários** e compilar **47 exemplos** com sucesso.

### 3. Testar Funcionalidades

```bash
# Classes e herança
codon run examples/intermediarios/classes.cd

# Generics
codon run examples/avancados/generics_complete.cd

# Maps
codon run examples/intermediarios/maps.cd

# Enums
codon run examples/intermediarios/enums.cd

# Array slicing
codon run examples/intermediarios/slicing.cd
```

### 4. Ver LLVM IR Gerado

```bash
codon build examples/basicos/hello_world.cd --quiet > output.ll
cat output.ll  # ou type output.ll no Windows
```

---

## Diferenciais do Projeto

- ✨ **Generics completos** com monomorphization
- ✨ **Maps** com suporte a múltiplos tipos de chave
- ✨ **Herança de classes** funcional
- ✨ **Enums** nativos
- ✨ **Array slicing** como Python
- ✨ **For-each** em arrays e strings
- ✨ **Instalador automático** multiplataforma
- ✨ **Comando global** `codon` utilizável de qualquer diretório
- ✨ **47 exemplos** validados
- ✨ **CI/CD** no GitHub Actions
- ✨ **Documentação completa** (3 manuais)

---

## Tecnologias Utilizadas

- **Python 3.10+**: Linguagem de implementação
- **llvmlite**: Geração e execução de LLVM IR
- **unittest**: Framework de testes
- **GitHub Actions**: CI/CD
- **PowerShell/Bash**: Scripts de automação

---

## Contato

- **Repositório:** https://github.com/leticia-pontes/codon
- **Autora:** Letícia Pontes
- **Licença:** MIT

---

**Data da entrega:** Dezembro de 2025
