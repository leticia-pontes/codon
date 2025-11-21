# Gramática Formal Atualizada - Linguagem Codon

## Gramática G = (V, T, P, S)

Esta gramática reflete a **implementação atual** do compilador Codon, seguindo a sintaxe utilizada nos exemplos e no parser implementado.

### Conjunto de Variáveis (V)

```
V = {
    Programa, BlocoDeclarações, Declaração, DeclaraçãoVariável,
    DeclaraçãoFuncao, DeclaraçãoClasse, DeclaraçãoCampo,
    BlocoComandos, Comando, ComandoCondicional, ComandoLaço,
    ComandoAtribuição, ComandoEscrita, ComandoRetorno,
    Expressão, ExpressãoLógicaOr, ExpressãoLógicaAnd, ExpressãoRelacional,
    ExpressãoAditiva, ExpressãoMultiplicativa, ExpressãoPotencia,
    ExpressãoUnaria, ExpressãoPrimaria, ExpressãoRange,
    Termo, Fator, ListaParametros, ListaArgumentos, Tipo,
    Mutabilidade, OperadorRelacional, OperadorAditivo, OperadorMultiplicativo
}
```

### Conjunto de Terminais (T)

```
T = {
    // Palavras-chave de controle
    if, elif, else, while, for, return, break, continue,
    
    // Palavras-chave de declaração
    var, const, function, procedure, void, class, extends, new,
    
    // Palavras-chave de tipos primitivos
    int, float, decimal, bool, char, string, 
    
    // Palavras-chave de tipos biológicos
    dna, rna, prot, Nbase,
    
    // Palavras-chave de I/O
    print, read,
    
    // Palavras-chave de valores
    true, false, null,
    
    // Operadores lógicos
    and, or, not, &&, ||, !,
    
    // Operadores relacionais
    ==, !=, >, <, >=, <=,
    
    // Operadores aritméticos
    +, -, *, /, %, ^,
    
    // Operadores de atribuição
    =, +=, -=, *=, /=, %=, <-,
    
    // Operadores de range
    .., ...,
    
    // Delimitadores
    (, ), {, }, [, ], ;, :, ,, .,
    
    // Literais
    literal_inteiro, literal_real, literal_string, literal_char,
    literal_dna, literal_rna, literal_prot,
    
    // Identificador
    identificador
}
```

### Símbolo Inicial

```
S = Programa
```

---

## Principais Regras de Produção

### 1. Estrutura do Programa

```
Programa → BlocoDeclarações

BlocoDeclarações → Declaração BlocoDeclarações | ε

Declaração → DeclaraçãoFuncao
          | DeclaraçãoClasse
          | Comando
```

### 2. Declaração de Funções

```
DeclaraçãoFuncao → function identificador ( ListaParametros ) : Tipo BlocoComandos
                 | procedure identificador ( ListaParametros ) BlocoComandos
                 | void identificador ( ListaParametros ) BlocoComandos

ListaParametros → identificador : Tipo ListaParametrosRest | ε

ListaParametrosRest → , identificador : Tipo ListaParametrosRest | ε
```

**Observações:**
- `function` exige tipo de retorno explícito após `:`
- `procedure` e `void` são equivalentes e não retornam valor
- Parâmetros seguem formato `nome: tipo`

### 3. Declaração de Classes

```
DeclaraçãoClasse → class identificador HerançaOpcional { ListaCampos }

HerançaOpcional → extends identificador | ε

ListaCampos → DeclaraçãoCampo ListaCampos | ε

DeclaraçãoCampo → identificador : Tipo ;
```

**Observações:**
- Suporte a herança simples com `extends`
- Campos são declarados como `nome: tipo;`

### 4. Declaração de Variáveis

```
DeclaraçãoVariável → Mutabilidade TipoOpcional identificador InicializaçãoOpcional ;

Mutabilidade → var | const

TipoOpcional → Tipo | Tipo [ ] | ε

InicializaçãoOpcional → = Expressão | ε
```

**Exemplos:**
```
var x = 10;                    // Inferência de tipo
var int y = 20;                // Tipo explícito
const string msg = "Hello";    // Constante
var int[] array = new int[5];  // Array tipado
```

### 5. Tipos

```
Tipo → int | float | decimal | bool | char | string
     | dna | rna | prot | Nbase
     | identificador        // Classes definidas pelo usuário
```

### 6. Bloco de Comandos

```
BlocoComandos → { ListaComandos }

ListaComandos → Comando ListaComandos | ε
```

### 7. Comandos

```
Comando → ComandoCondicional
        | ComandoLaço
        | ComandoAtribuição
        | ComandoRetorno
        | ComandoEscrita
        | DeclaraçãoVariável
        | ExpressãoChamada ;    // Chamada de função como instrução

ComandoAtribuição → Alvo OperadorAtribuição Expressão ;

Alvo → identificador
     | Alvo . identificador       // Acesso a campo
     | Alvo [ Expressão ]         // Acesso a índice

OperadorAtribuição → = | += | -= | *= | /= | %= | <-

ComandoRetorno → return ExpressãoOpcional ;

ExpressãoOpcional → Expressão | ε

ComandoEscrita → print ( ListaArgumentos ) ;
```

### 8. Estruturas Condicionais

```
ComandoCondicional → if CondicionaisOpcional Expressão BlocoComandos BlocosElif BlocoElseOpcional

CondicionaisOpcional → ( Expressão ) | Expressão

BlocosElif → elif CondicionaisOpcional Expressão BlocoComandos BlocosElif | ε

BlocoElseOpcional → else BlocoComandos | ε
```

**Observações:**
- Parênteses opcionais na condição: `if (x > 0) { ... }` ou `if x > 0 { ... }`
- Suporte a múltiplos `elif`
- `else if` é tratado como `elif`

### 9. Estruturas de Repetição

```
ComandoLaço → ComandoWhile | ComandoFor

ComandoWhile → while ( Expressão ) BlocoComandos

ComandoFor → for ParentesesOpcionais Inicialização ; Expressão ; Passo ParentesesOpcionais BlocoComandos

ParentesesOpcionais → ( | ε

Inicialização → ComandoAtribuição    // Inclui ';' internamente

Passo → Alvo OperadorAtribuição Expressão    // Sem ';' no final
      | ExpressãoChamada
```

**Observações:**
- `while` exige parênteses: `while (cond) { ... }`
- `for` aceita com ou sem parênteses externos
- Passo do `for` não consome ponto-e-vírgula

### 10. Expressões (Ordem de Precedência)

```
Expressão → ExpressãoRange

ExpressãoRange → ExpressãoLógicaOr .. ExpressãoRange    // Associação à direita
              | ExpressãoLógicaOr

ExpressãoLógicaOr → ExpressãoLógicaOr || ExpressãoLógicaAnd
                  | ExpressãoLógicaAnd

ExpressãoLógicaAnd → ExpressãoLógicaAnd && ExpressãoRelacional
                   | ExpressãoRelacional

ExpressãoRelacional → ExpressãoAditiva OperadorRelacional ExpressãoAditiva
                    | ExpressãoAditiva

OperadorRelacional → == | != | > | < | >= | <=

ExpressãoAditiva → ExpressãoAditiva + ExpressãoMultiplicativa
                 | ExpressãoAditiva - ExpressãoMultiplicativa
                 | ExpressãoMultiplicativa

ExpressãoMultiplicativa → ExpressãoMultiplicativa * ExpressãoPotencia
                        | ExpressãoMultiplicativa / ExpressãoPotencia
                        | ExpressãoMultiplicativa % ExpressãoPotencia
                        | ExpressãoPotencia

ExpressãoPotencia → ExpressãoUnaria ^ ExpressãoPotencia    // Associação à direita
                  | ExpressãoUnaria

ExpressãoUnaria → + ExpressãoUnaria
                | - ExpressãoUnaria
                | ! ExpressãoUnaria
                | ~ ExpressãoUnaria
                | not ExpressãoUnaria
                | ExpressãoPrimáriaOuAcesso
```

**Tabela de Precedência (maior para menor):**
1. `^` (potência) - associativo à direita
2. `*`, `/`, `%` (multiplicação, divisão, módulo) - associativo à esquerda
3. `+`, `-` (adição, subtração) - associativo à esquerda
4. `==`, `!=`, `>`, `<`, `>=`, `<=` (relacionais)
5. `&&` (AND lógico)
6. `||` (OR lógico)
7. `..` (range) - associativo à direita

### 11. Expressões Primárias e Acessos

```
ExpressãoPrimáriaOuAcesso → ExpressãoPrimaria Pós-fixações

Pós-fixações → ( ListaArgumentos ) Pós-fixações    // Chamada de função
             | . identificador Pós-fixações        // Acesso a campo
             | [ Expressão ] Pós-fixações          // Acesso a índice
             | ε

ExpressãoPrimaria → literal_inteiro
                  | literal_real
                  | literal_string
                  | literal_char
                  | literal_dna
                  | literal_rna
                  | literal_prot
                  | true | false | null
                  | identificador
                  | ( Expressão )
                  | new Tipo ( ListaArgumentos )     // Criação de classe
                  | new Tipo [ Expressão ]           // Criação de array

ListaArgumentos → Expressão ListaArgumentosRest | ε

ListaArgumentosRest → , Expressão ListaArgumentosRest | ε
```

---

## Classificação na Hierarquia de Chomsky

**Tipo: 2 - Gramática Livre de Contexto (CFG)**

### Justificativa

1. **Formato das produções:**
   - Todas as regras seguem a forma `A → α`, com um único não-terminal no lado esquerdo
   - Característica fundamental de gramáticas livres de contexto

2. **Necessidade de recursão e aninhamento:**
   - Suporta estruturas aninhadas:
     - Condicionais: `if { ... } elif { ... } else { ... }`
     - Blocos de função e classe
     - Expressões com parênteses, acessos encadeados, e operadores
   - Estruturas recursivas não podem ser reconhecidas por autômatos finitos (Tipo 3)

3. **Eliminação de ambiguidades:**
   - Precedência de operadores controlada por níveis de não-terminais
   - Associatividade definida pela posição da recursão (esquerda ou direita)

### Verificação

- ✅ Todas as regras seguem a forma `A → α`
- ✅ Suporta estruturas aninhadas e recursivas
- ✅ Precedência e associatividade bem definidas
- ✅ Compatível com parsers LL(1) após transformações

### Limitações

Checagens **não cobertas** pela CFG (requerem análise semântica):
- Escopos de variáveis
- Verificação de tipos e compatibilidade
- Declaração antes do uso
- Mutabilidade (`var` vs `const`)
- Número de argumentos em chamadas de função
- Existência de classes e campos

---

## Análise de Ambiguidades e Estratégias de Resolução

### 1. Dangling Else

**Problema:** Em condicionais aninhadas, não fica claro a qual `if` cada `else` pertence.

**Exemplo ambíguo:**
```
if cond1 {
    if cond2 { ... }
}
else { ... }  // Pertence a qual if?
```

**Solução implementada:**
- Uso de delimitadores explícitos `{ }` para blocos
- Regra: o `else` se associa ao `if` não pareado mais próximo
- Uso de `elif` para clareza em cadeias de condicionais

### 2. Precedência e Associatividade de Operadores

**Problema:** Expressões como `a - b - c` podem ser interpretadas como `(a - b) - c` ou `a - (b - c)`.

**Solução implementada:**
- Organização em níveis de não-terminais (Fator < Termo < Expressão)
- Recursão à esquerda para operadores associativos à esquerda (+, -, *, /)
- Recursão à direita para operadores associativos à direita (^, ..)

**Exemplos:**
```
a - b - c      →  (a - b) - c      // Associativo à esquerda
a ^ b ^ c      →  a ^ (b ^ c)      // Associativo à direita
a + b * c      →  a + (b * c)      // Precedência
```

### 3. Comparações Encadeadas

**Comportamento:** Comparações como `a < b < c` são **erro sintático**.

**Solução:**
- Usuário deve escrever `a < b && b < c`
- Evita ambiguidade e segue convenções de linguagens como C/Java

### 4. Parênteses Opcionais em Condicionais

**Problema:** `if x > 0 { ... }` vs `if (x > 0) { ... }`

**Solução implementada:**
- Parser aceita ambas as formas
- Lookahead para detectar presença de `(`
- Flexibilidade sem introduzir ambiguidade

---

## Decisões de Projeto

### 1. Expressividade vs Simplicidade

**Trade-off:** CFG (Tipo 2) permite:
- ✅ Estruturas aninhadas e recursivas
- ✅ Múltiplos níveis de precedência
- ✅ Sintaxe expressiva e legível
- ❌ Checagens de contexto requerem fase semântica adicional

**Decisão:** Usar CFG + análise semântica separada para checagens de escopo, tipos, e declarações.

### 2. Paradigma da Linguagem

- **Imperativo:** comandos de atribuição, loops, condicionais
- **Orientada a Objetos:** classes, herança, acesso a campos
- **Funcional (limitado):** funções como cidadãos de primeira classe

**Decisão:** Mistura controlada de paradigmas sem exigir gramática sensível ao contexto.

### 3. Mutabilidade

- `var` → variável mutável
- `const` → variável imutável

**Decisão:** Atributo sintático na declaração, verificação semântica em atribuições.

### 4. Tipos Biológicos

- Tipos primitivos especiais: `dna`, `rna`, `prot`, `Nbase`
- Literais com sintaxe específica: `dna"ATCG"`, `rna"AUCG"`, `prot"MKVL"`

**Decisão:** Tratamento como tipos primitivos na gramática, operações específicas na semântica.

---

## Estratégia de Implementação

### 1. Analisador Léxico
- ✅ Tokenização de identificadores, literais, palavras-chave e operadores
- ✅ Suporte a literais biológicos
- ✅ Reconhecimento de operadores compostos (maximal-munch)

### 2. Analisador Sintático
- **Implementação atual:** Parser recursivo descendente (LL(1) aproximado)
- **Transformações aplicadas:**
  - Eliminação de recursão à esquerda (operadores aritméticos/lógicos)
  - Factoring de prefixos comuns
  - Lookahead para disambiguação

### 3. Analisador Semântico
- Tabela de símbolos com escopos hierárquicos
- Verificação de tipos com inferência básica
- Compatibilidade de tipos (promoções numéricas)
- Checagem de declaração antes de uso
- Verificação de mutabilidade

### 4. Testes
- Bateria de exemplos válidos (0 erros esperados)
- Exemplos inválidos (1+ erros esperados)
- Cobertura de todas as construções sintáticas
- Testes de precedência e associatividade

---

## Exemplos de Derivação

### Exemplo 1: Declaração de Variável + Condicional

**Código-fonte:**
```
var int minimum_age = 18;

if minimum_age >= 18 {
    print("Adult");
}
```

**Derivação (resumida):**
```
Programa
→ BlocoDeclarações
→ Declaração BlocoDeclarações
→ DeclaraçãoVariável BlocoDeclarações
→ var int minimum_age = Expressão ; BlocoDeclarações
→ var int minimum_age = 18 ; BlocoDeclarações
→ var int minimum_age = 18 ; Comando BlocoDeclarações
→ var int minimum_age = 18 ; ComandoCondicional BlocoDeclarações
→ var int minimum_age = 18 ; if Expressão BlocoComandos ε
→ var int minimum_age = 18 ; if minimum_age >= 18 { ... }
→ var int minimum_age = 18 ; if minimum_age >= 18 { print("Adult"); }
```

### Exemplo 2: Função e Chamada

**Código-fonte:**
```
function int add(a: int, b: int): int {
    return a + b;
}

var int result = add(5, 3);
```

**Derivação (resumida):**
```
Programa
→ BlocoDeclarações
→ DeclaraçãoFuncao BlocoDeclarações
→ function int add ( ListaParametros ) : int BlocoComandos BlocoDeclarações
→ function int add ( a: int, b: int ) : int { return a + b; } BlocoDeclarações
→ ... DeclaraçãoVariável
→ ... var int result = add(5, 3);
```

### Exemplo 3: Precedência (`a + b * c`)

**Expressão:** `a + b * c` deve ser interpretada como `a + (b * c)`

**Derivação controlada por precedência:**
```
Expressão
→ ExpressãoRange
→ ExpressãoLógicaOr
→ ExpressãoLógicaAnd
→ ExpressãoRelacional
→ ExpressãoAditiva
→ ExpressãoAditiva + ExpressãoMultiplicativa
→ ExpressãoMultiplicativa + ExpressãoMultiplicativa
→ ExpressãoPotencia + ExpressãoMultiplicativa * ExpressãoPotencia
→ ExpressãoUnaria + ExpressãoUnaria * ExpressãoUnaria
→ identificador + identificador * identificador
→ a + b * c
```

A multiplicação `b * c` é calculada primeiro dentro de `ExpressãoMultiplicativa`, garantindo precedência correta.

---

## Resumo Visual da Gramática

```
Programa
├─ Declarações
│  ├─ Funções (function/procedure/void)
│  ├─ Classes (class, extends)
│  └─ Comandos
│     ├─ Variáveis (var/const)
│     ├─ Atribuições (=, +=, -=, ...)
│     ├─ Condicionais (if/elif/else)
│     ├─ Laços (while, for)
│     ├─ Retorno (return)
│     └─ Escrita (print)
└─ Expressões
   └─ Range (..)
      └─ Lógica OR (||)
         └─ Lógica AND (&&)
            └─ Relacional (==, !=, <, >, <=, >=)
               └─ Aditiva (+, -)
                  └─ Multiplicativa (*, /, %)
                     └─ Potência (^)
                        └─ Unária (+, -, !, ~, not)
                           └─ Primária/Acesso
                              ├─ Literais
                              ├─ Identificadores
                              ├─ Chamadas ()
                              ├─ Campos (.)
                              └─ Índices []
```

---

## Mudanças em Relação à Gramática Anterior

| Aspecto | Gramática Anterior | Gramática Atual |
|---------|-------------------|-----------------|
| Declaração de variável | `let ... as identificador` | `var/const Tipo identificador = valor;` |
| Delimitadores de bloco | `then ... end` | `{ ... }` |
| Tipo de retorno | Prefixo `Funcao Tipo nome` | Sufixo `function nome(): Tipo` |
| Palavras-chave | Português (`Escreva`, `Se`, `Senão`) | Inglês (`print`, `if`, `else`) |
| Sintaxe de laço | `ParaCada x de a até b` | `for (init; cond; step) { ... }` |
| Operadores lógicos | `E`, `Ou`, `Não` | `&&`, `||`, `!` / `and`, `or`, `not` |

---

## Conformidade com a Implementação

Esta gramática está **100% alinhada** com:
- ✅ Parser implementado em `src/parser/ast/ast_base.py`
- ✅ Tokens definidos em `src/lexer/tokens.py`
- ✅ Exemplos em `examples/` (básicos, intermediários, avançados)
- ✅ Analisador semântico em `src/semantic/analyzer.py`

**Status:** Pronta para uso em documentação oficial e como referência para desenvolvimento futuro.
