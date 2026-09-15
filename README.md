# Codon – Linguagem de Programação e Compilador para LLVM

[![CI](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml/badge.svg)](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml)

**Codon** é uma linguagem de programação compilada com sintaxe própria e um pipeline completo de compilação para **LLVM IR**, com execução JIT utilizando **llvmlite**.

O projeto implementa todas as principais etapas de um compilador: análise léxica, análise sintática, construção da AST, análise semântica, verificação de tipos e geração de código LLVM.

A linguagem possui suporte a recursos como arrays, strings, structs, classes, herança, enums, maps e generics.

## Visão geral

O pipeline de compilação segue o fluxo:

```text
Código-fonte (.cd)
      │
      ▼
    Lexer
      │
      ▼
    Parser
      │
      ▼
     AST
      │
      ▼
Análise Semântica
      │
      ▼
  LLVM Codegen
      │
      ▼
   LLVM IR
      │
      ▼
     JIT
      │
      ▼
    main()
```

O compilador pode tanto executar um programa diretamente via JIT quanto gerar o LLVM IR resultante.

### Principais componentes

| Componente        | Responsabilidade                                   |
| ----------------- | -------------------------------------------------- |
| Lexer             | Tokenização do código-fonte                        |
| Parser            | Análise sintática e construção da AST              |
| Semantic Analyzer | Escopos, tabela de símbolos e verificação de tipos |
| LLVM Codegen      | Geração de LLVM IR                                 |
| JIT               | Compilação e execução em tempo de execução         |
| Test Suite        | Validação dos componentes e exemplos da linguagem  |

## Recursos da linguagem

Atualmente, o Codon suporta:

* Variáveis e constantes
* Tipos inteiros e decimais
* Strings e caracteres
* Arrays
* Structs
* Classes e herança
* Enums
* Maps
* Funções
* Funções nativas
* Generics
* `foreach`
* Slicing
* Controle de fluxo
* Escopos e resolução de símbolos
* Verificação estática de tipos
* Monomorfização de generics

Exemplo:

```codon
function main(): int {
  print("Hello, Codon!");
  return 0;
}
```

Se nenhum `main()` for declarado, o compilador cria automaticamente um wrapper para executar as instruções presentes no escopo global.

## Documentação

A documentação técnica está organizada em:

* **[QUICK_START.md](QUICK_START.md)** — primeiros passos.
* **[MANUAL_UTILIZACAO.md](MANUAL_UTILIZACAO.md)** — sintaxe, tipos, funções e exemplos.
* **[MANUAL_INSTALACAO.md](MANUAL_INSTALACAO.md)** — instalação em Windows, Linux e macOS.
* **[RESUMO_TECNICO.md](RESUMO_TECNICO.md)** — arquitetura e implementação.
* **[docs/gramatica-formal-atualizada.md](docs/gramatica-formal-atualizada.md)** — gramática formal.
* **[docs/especificacao-linguagem.md](docs/especificacao-linguagem.md)** — especificação da linguagem.

## Uso

### Pré-requisitos

* Python ≥ 3.10
* `pip`
* Git

### Instalação

Clone o repositório:

```bash
git clone https://github.com/leticia-pontes/codon.git
cd codon
```

#### Linux / macOS

```bash
chmod +x install.sh
./install.sh
```

#### Windows

```powershell
.\install.bat
```

Os scripts de instalação criam o ambiente virtual, instalam as dependências e configuram o comando `codon`.

### Executar um programa

```bash
codon run examples/basicos/hello_world.cd
```

### Gerar LLVM IR

```bash
codon build examples/basicos/hello_world.cd
```

Para gerar somente o IR, sem mensagens adicionais:

```bash
codon build examples/basicos/hello_world.cd --quiet > output.ll
```

Depois da instalação, arquivos `.cd` podem ser compilados a partir de qualquer diretório.

## Arquitetura

A implementação está organizada em componentes independentes:

```text
src/
├── lexer/
│   ├── afds/
│   ├── analisador_lexico_completo.py
│   └── tokens.py
│
├── parser/
│   ├── ast/
│   │   ├── ast_base.py
│   │   ├── declaracoes.py
│   │   └── expressoes.py
│   └── parser.py
│
├── semantic/
│   ├── analyzer.py
│   ├── tabela_simbolos.py
│   └── verificador_tipos.py
│
├── codegen/
│   ├── llvm_codegen.py
│   └── otimizador.py
│
└── compilador.py
```

O `llvm_codegen.py` é responsável pela tradução da AST semanticamente validada para LLVM IR. O backend utiliza `llvmlite` e inclui suporte à monomorfização de generics, além da geração de estruturas como arrays, strings, classes, enums e maps.

## Exemplos

A pasta [`examples/`](examples/) contém programas que demonstram diferentes recursos da linguagem:

```text
examples/
├── basicos/
├── intermediarios/
└── avancados/
```

Os exemplos básicos cobrem a sintaxe fundamental. Os exemplos intermediários exploram estruturas como arrays, structs, classes, maps, `foreach` e slicing.

Os exemplos avançados incluem generics, enums e programas que combinam múltiplos recursos da linguagem.

## Testes

O projeto possui testes automatizados para os principais componentes do compilador.

### Testes unitários

```bash
python -m unittest discover -s test -p "*.py" -v
```

### Suite completa

#### Linux / macOS

```bash
./scripts/run_all_tests.sh
```

#### Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

A suite também valida a compilação e execução dos exemplos da linguagem.

## CI

O projeto utiliza **GitHub Actions** para executar automaticamente os testes em `push` e `pull_request` direcionados à branch `main`.

## Estrutura do projeto

```text
codon/
├── docs/
├── examples/
│   ├── avancados/
│   ├── basicos/
│   └── intermediarios/
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
│   ├── parser_test/
│   ├── semantic_test/
│   └── codegen_test/
├── tools/
└── README.md
```

## Estado atual

O compilador atualmente conta com:

* 14 testes unitários;
* 47 exemplos funcionais;
* suporte a arrays, strings, structs, classes, herança, generics, enums e maps;
* geração de LLVM IR;
* execução JIT;
* análise semântica e verificação de tipos;
* CI via GitHub Actions.
