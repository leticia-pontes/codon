# Codon – Linguagem e Compilador Educacional (LLVM)

[![CI](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml/badge.svg)](https://github.com/leticia-pontes/codon/actions/workflows/ci.yml)

> **Nome provisório:** Codon
>
> **Objetivo:** Linguagem educativa com foco didático (inclui tipos biológicos), compilando para **LLVM IR** com execução JIT via llvmlite.

---

## Sumário

* [Visão Geral](#visão-geral)

  * [Fluxo do Compilador](#fluxo-do-compilador)
* [Manuais](#-manuais)
* [Manual de Utilização](#manual-de-utilização)
* [Instalação (passo a passo)](#instalação-passo-a-passo)

  * [Instalação Automática (Recomendado)](#instalação-automática-recomendado)
  * [Uso após instalação](#uso-após-instalação)
  * [Instalação Manual (Alternativa)](#instalação-manual-alternativa)
* [Componentes do Compilador](#componentes-do-compilador)
* [Léxico / Tokens](#léxico--tokens)
* [Sintaxe / Gramática](#sintaxe--gramática)
* [Exemplos](#exemplos)
* [Executar Testes](#executar-testes)
* [Perguntas Frequentes](#perguntas-frequentes)
* [CI - GitHub Actions](#ci---github-actions)
* [Estrutura do Projeto](#estrutura-do-projeto)
* [Entrega](#entrega)
* [Como Contribuir](#como-contribuir)
* [Licença](#licença)

---

## Visão Geral

O **Codon** oferece uma linguagem simples e expressiva, com pipeline completo de compilação: **Analisador Léxico (lexer)**, **Analisador Sintático (parser/AST)**, **Analisador Semântico** e **Gerador de Código** para **LLVM IR**. A execução é feita via JIT (llvmlite), chamando a função `main`.

### Fluxo do Compilador (resumo)

```
fonte (.cd)
  ├─► Lexer (tokens)
  ├─► Parser (AST)
  ├─► Analisador Semântico (escopos, tipos)
  └─► Codegen (LLVM IR) ──► JIT (executa main)
```

---

## Manuais

Para documentação completa, consulte:

- **[MANUAL_INSTALACAO.md](MANUAL_INSTALACAO.md)** - Guia passo a passo para leigos (Windows, Linux, macOS)
- **[MANUAL_UTILIZACAO.md](MANUAL_UTILIZACAO.md)** - Sintaxe completa, tipos, funções, exemplos
- **[QUICK_START.md](QUICK_START.md)** - Guia rápido de início

---

## Manual de Utilização

> **Requisitos:** Python ≥ 3.10 e `pip`

Após a instalação (veja seção abaixo), você pode usar o comando `codon` de **qualquer diretório**:

```bash
# Compilar e executar (JIT)
codon run meu_programa.cd
codon run examples/basicos/hello_world.cd

# Apenas compilar (imprime LLVM IR com mensagens informativas)
codon build meu_programa.cd

# Compilar sem mensagens (ideal para salvar em arquivo)
codon build meu_programa.cd --quiet > output.ll
```

**Programa mínimo:**

```codon
function main(): int {
  print("Hello, Codon!");
  return 0;
}
```

> **Nota:** Se não houver função `main()`, o compilador cria automaticamente um wrapper que executa as instruções de topo.

---

## Instalação (passo a passo)

### Instalação Automática (Recomendado)

**Windows (PowerShell):**

```powershell
git clone https://github.com/leticia-pontes/codon.git
cd codon
.\install.bat
```

**Linux / macOS (bash):**

```bash
git clone https://github.com/leticia-pontes/codon.git
cd codon
chmod +x install.sh
./install.sh
```

O script automaticamente:
1. Cria ambiente virtual (`.venv`)
2. Instala dependências (`llvmlite`)
3. Instala o comando `codon` globalmente

### Uso após instalação

**Ative o ambiente virtual** (necessário apenas uma vez por sessão):

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.\.venv\Scripts\activate
```

Agora use `codon` de **qualquer diretório**:

```bash
codon run ~/meus_projetos/teste.cd
codon build ./programa.cd > saida.ll
```

### Instalação Manual (Alternativa)

```bash
git clone https://github.com/leticia-pontes/codon.git
cd codon

# Criar e ativar venv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# OU
.\.venv\Scripts\activate   # Windows

# Instalar
pip install -r requirements.txt
pip install -e .
```

---

## Componentes do Compilador

- Léxico: `src/lexer/analisador_lexico_completo.py` (tokens, `TokenStream`).
- Sintático/AST: `src/parser/ast/ast_base.py`, `src/parser/parser.py` (constrói a AST).
- Semântico: `src/semantic/analyzer.py` (escopos, tabela de símbolos, verificação de tipos).
- Codegen: `src/codegen/llvm_codegen.py` (gera LLVM IR com llvmlite; generics por monomorfização; arrays, strings, classes, enums, maps, etc.).
- Execução/JIT: `src/compilador.py` (liga tudo, verifica e executa `main`).

---

## Léxico / Tokens

O lexer converte texto em tokens (identificadores, palavras-chave, literais, operadores). Espaços e comentários são ignorados; strings suportam escapes (`\n`, `\t`, `\\`, `\"`).

Números suportam inteiros e decimais.

Exemplo de token:

```text
Token(kind, lexeme, literal, line, col)
```

A lista termina sempre com `EOF`.

---

## Sintaxe / Gramática

A gramática completa e atualizada está em `docs/gramatica-formal-atualizada.md` e a especificação da linguagem em `docs/especificacao-linguagem.md`.

---



## Exemplos

Veja a pasta `examples/`:
- `basicos/hello_world.cd` – sintaxe mínima.
- `intermediarios/` – arrays, structs, classes, maps, foreach, slicing.
- `avancados/` – generics (funções, classes, structs), enums, exemplos completos.
---

## Executar Testes

**Ative o venv primeiro** (se ainda não estiver ativo):

```bash
source .venv/bin/activate  # Linux/macOS
.\.venv\Scripts\activate   # Windows
```

**Rodar testes unitários:**

```bash
python -m unittest discover -s test -p "*.py" -v
```

**Rodar testes completos + compilação de exemplos:**

```bash
# Linux/macOS
./scripts/run_all_tests.sh

# Windows (PowerShell)
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

**Teste rápido:**

```bash
# De qualquer diretório, após ativar venv:
codon run examples/basicos/hello_world.cd
```

---

## Perguntas Frequentes

**P: Preciso ativar o venv toda vez?**  
R: Sim, mas apenas uma vez por sessão do terminal. Depois de ativar, o comando `codon` funciona de qualquer diretório.

**P: Posso criar um executável .exe?**  
R: Sim! Use ferramentas como PyInstaller ou cx_Freeze para empacotar o compilador em um binário standalone. Isso eliminaria a necessidade do venv.

**P: O comando não funciona de outro diretório**  
R: Verifique se:
1. O venv está ativado (`source .venv/bin/activate` ou `.\.venv\Scripts\activate`)
2. A instalação foi concluída (`pip install -e .`)
3. Use caminhos absolutos ou relativos corretos para os arquivos `.cd`

**P: Como desinstalar?**  
R: `pip uninstall codon-compiler` (dentro do venv) ou delete a pasta `codon/` inteira.

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

## Entrega

**Link do repositório do projeto:**

https://github.com/leticia-pontes/codon

### ✅ Checklist de Requisitos

Conforme especificação da disciplina, o projeto entrega:

- ✅ **Manual de utilização** → [MANUAL_UTILIZACAO.md](MANUAL_UTILIZACAO.md)
  - Sintaxe completa da linguagem
  - Tipos de dados, operadores, estruturas de controle
  - Funções, arrays, strings, structs, classes, enums
  - Generics e maps
  - Funções nativas
  - Exemplos completos

- ✅ **Manual de instalação para leigo** → [MANUAL_INSTALACAO.md](MANUAL_INSTALACAO.md)
  - Passo a passo detalhado para Windows, Linux e macOS
  - Instalação de pré-requisitos (Python)
  - Script automático de instalação
  - Verificação e primeiro programa
  - Solução de problemas comuns

- ✅ **Analisador Léxico (Lexer)**
  - Implementação: `src/lexer/analisador_lexico_completo.py`
  - Tokens: `src/lexer/tokens.py`
  - AFDs: `src/lexer/afds/`
  - Testes: `test/lexer_test/`

- ✅ **Analisador Sintático (Parser - AST)**
  - Parser principal: `src/parser/ast/ast_base.py`
  - Nós da AST: `src/parser/ast/declaracoes.py`, `src/parser/ast/expressoes.py`
  - Gramática formal: `docs/gramatica-formal-atualizada.md`
  - Testes: `test/parser_test/`

- ✅ **Analisador Semântico**
  - Implementação: `src/semantic/analyzer.py`
  - Tabela de símbolos: `src/semantic/tabela_simbolos.py`
  - Verificação de tipos: `src/semantic/verificador_tipos.py`
  - Testes: `test/semantic_test/`

- ✅ **Gerador de Código (LLVM IR)**
  - Codegen principal: `src/codegen/llvm_codegen.py`
  - Otimizador: `src/codegen/otimizador.py`
  - Suporte a generics (monomorphization)
  - Testes: `test/codegen_test/`

### 📊 Estatísticas do Projeto

- **14 testes unitários** (lexer, parser, semântico, codegen)
- **47 exemplos funcionais** compilados e validados
- **Cobertura completa** de features: arrays, strings, classes, herança, generics, enums, maps
- **CI/CD** via GitHub Actions

---

## Como Contribuir

1. Fork → branch → PR.
2. Inclua testes.
3. Atualize `docs/` quando necessário.

> Contribuições restritas ao grupo no momento.
