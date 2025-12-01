# Manual de Utilização - Linguagem Codon

## Sumário

* [Introdução](#introdução)
* [Comandos do Compilador](#comandos-do-compilador)
* [Estrutura Básica de um Programa](#estrutura-básica-de-um-programa)
* [Tipos de Dados](#tipos-de-dados)
* [Variáveis e Constantes](#variáveis-e-constantes)
* [Operadores](#operadores)
* [Estruturas de Controle](#estruturas-de-controle)
* [Funções](#funções)
* [Arrays](#arrays)
* [Strings](#strings)
* [Structs](#structs)
* [Classes e Objetos](#classes-e-objetos)
* [Enums](#enums)
* [Generics (Tipos Genéricos)](#generics-tipos-genéricos)
* [Maps (Dicionários)](#maps-dicionários)
* [Funções Nativas](#funções-nativas)
* [Exemplos Completos](#exemplos-completos)

---

## Introdução

**Codon** é uma linguagem educacional compilada para LLVM IR, com sintaxe inspirada em C/Java e foco em facilidade de aprendizado. O compilador gera código LLVM IR que pode ser executado via JIT (Just-In-Time).

### Características principais:

- Tipagem estática com inferência
- Suporte a programação procedural e orientada a objetos
- Generics (polimorfismo paramétrico)
- Gerenciamento automático de memória (alocação)
- Arrays, strings, structs, classes, enums e maps
- Compilação para LLVM IR

---

## Comandos do Compilador

### Executar um programa

```bash
codon run programa.cd
```

Compila e executa o programa imediatamente via JIT.

### Compilar (gerar LLVM IR)

```bash
# Modo normal (mostra progresso)
codon build programa.cd

# Modo quiet (salva LLVM IR em arquivo)
codon build programa.cd --quiet > output.ll
```

### Ajuda

```bash
codon run
# ou
codon build
```

Exibe instruções de uso.

---

## Estrutura Básica de um Programa

Todo programa Codon deve ter uma função `main` que serve como ponto de entrada:

```codon
function main(): int {
    print("Hello, Codon!");
    return 0;
}
```

**Regras:**
- `main()` deve retornar `int` (código de saída)
- Se não houver `main`, o compilador cria um wrapper automático
- Comentários de linha: `// comentário`
- Comentários de bloco: `/* comentário */`

---

## Tipos de Dados

### Tipos Primitivos

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `int` | Inteiro 32 bits | `42`, `-10` |
| `double` | Ponto flutuante 64 bits | `3.14`, `-0.5` |
| `bool` | Booleano | `true`, `false` |
| `string` | Cadeia de caracteres | `"Hello"` |
| `void` | Sem retorno (apenas funções) | - |

### Tipos Compostos

- **Arrays**: `int[]`, `string[]`, `double[]`
- **Structs**: Tipos definidos pelo usuário
- **Classes**: Tipos com herança e métodos
- **Enums**: Enumerações
- **Maps**: Dicionários chave-valor

---

## Variáveis e Constantes

### Declaração de Variáveis

```codon
// Com tipo explícito
let x: int = 10;
let nome: string = "Codon";
let ativo: bool = true;

// Com inferência de tipo
let y = 20;           // int
let pi = 3.14159;     // double
let mensagem = "Hi";  // string
```

### Atribuição

```codon
x = 15;
nome = "Nova String";
ativo = false;
```

### Escopo

Variáveis têm escopo de bloco `{}`:

```codon
function main(): int {
    let x: int = 10;  // Visível em toda a função
    {
        let y: int = 20;  // Visível apenas neste bloco
        print(x + y);     // OK: 30
    }
    // print(y);  // ERRO: y não existe aqui
    return 0;
}
```

---

## Operadores

### Aritméticos

```codon
let a = 10 + 5;   // Adição: 15
let b = 10 - 3;   // Subtração: 7
let c = 4 * 5;    // Multiplicação: 20
let d = 20 / 4;   // Divisão: 5
let e = 17 % 5;   // Módulo (resto): 2
let f = 2 ** 3;   // Potência: 8
```

### Comparação

```codon
10 == 10   // Igual: true
10 != 5    // Diferente: true
10 > 5     // Maior: true
10 >= 10   // Maior ou igual: true
5 < 10     // Menor: true
5 <= 5     // Menor ou igual: true
```

### Lógicos

```codon
true && false   // E lógico: false
true || false   // OU lógico: true
!true           // NÃO lógico: false
```

### Bitwise

```codon
let a = 5 & 3;    // AND: 1
let b = 5 | 3;    // OR: 7
let c = 5 ^ 3;    // XOR: 6
let d = ~5;       // NOT: -6
let e = 5 << 1;   // Shift left: 10
let f = 5 >> 1;   // Shift right: 2
```

### Incremento/Decremento

```codon
let x = 5;
x++;    // x = 6
x--;    // x = 5
++x;    // x = 6
--x;    // x = 5
```

### Atribuição Composta

```codon
x += 5;   // x = x + 5
x -= 3;   // x = x - 3
x *= 2;   // x = x * 2
x /= 4;   // x = x / 4
```

---

## Estruturas de Controle

### If / Else

```codon
let idade = 18;

if idade >= 18 {
    print("Maior de idade");
} else if idade >= 13 {
    print("Adolescente");
} else {
    print("Criança");
}
```

### While

```codon
let i = 0;
while i < 5 {
    print(i);
    i++;
}
```

### For

```codon
// For clássico
for let i = 0; i < 10; i++ {
    print(i);
}

// For-each em arrays
let nums: int[] = [1, 2, 3, 4, 5];
for item in nums {
    print(item);
}

// For-each em strings
let texto = "Hello";
for char in texto {
    print(char);
}
```

### Break e Continue

```codon
for let i = 0; i < 10; i++ {
    if i == 3 {
        continue;  // Pula para próxima iteração
    }
    if i == 7 {
        break;     // Sai do loop
    }
    print(i);
}
```

---

## Funções

### Declaração

```codon
// Função com retorno
function soma(a: int, b: int): int {
    return a + b;
}

// Função sem retorno (void/procedure)
function imprimir_mensagem(msg: string): void {
    print(msg);
}

// Ou use 'procedure' (equivalente a void)
procedure saudar(nome: string) {
    print("Olá, " + nome + "!");
}
```

### Chamada

```codon
let resultado = soma(5, 3);
imprimir_mensagem("Hello");
saudar("Maria");
```

### Parâmetros e Retorno

```codon
function calcular(x: double, y: double): double {
    let resultado = x * y + 10.5;
    return resultado;
}

function main(): int {
    let valor = calcular(3.5, 2.0);
    print(valor);  // 17.5
    return 0;
}
```

### Recursão

```codon
function fibonacci(n: int): int {
    if n <= 1 {
        return n;
    }
    return fibonacci(n - 1) + fibonacci(n - 2);
}

function main(): int {
    print(fibonacci(10));  // 55
    return 0;
}
```

---

## Arrays

### Declaração e Inicialização

```codon
// Array literal
let numeros: int[] = [1, 2, 3, 4, 5];
let nomes: string[] = ["Ana", "João", "Maria"];

// Array com tamanho fixo (new)
let valores: int[] = new int[10];

// Array multidimensional
let matriz: int[][] = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
];
```

### Acesso

```codon
let primeiro = numeros[0];   // 1
let segundo = numeros[1];    // 2
numeros[2] = 10;             // Modifica elemento
```

### Métodos de Array

```codon
let arr: int[] = [1, 2, 3];

// Adicionar elemento
arr.push(4);         // [1, 2, 3, 4]

// Remover último elemento
let ultimo = arr.pop();  // 4, arr = [1, 2, 3]

// Tamanho
let tamanho = arr.length();  // 3
```

### Slicing (Fatiamento)

```codon
let numeros: int[] = [0, 1, 2, 3, 4, 5];

let parte1 = numeros[1:4];   // [1, 2, 3]
let parte2 = numeros[:3];    // [0, 1, 2]
let parte3 = numeros[3:];    // [3, 4, 5]
```

---

## Strings

### Operações Básicas

```codon
let s1 = "Hello";
let s2 = "World";

// Concatenação
let s3 = s1 + " " + s2;  // "Hello World"

// Acesso a caractere
let primeiro_char = s1[0];  // 'H'

// Tamanho
let tamanho = strlen(s1);   // 5
```

### Comparação

```codon
let a = "abc";
let b = "abc";

if a == b {
    print("Strings iguais");
}
```

### Iteração

```codon
let palavra = "Codon";
for char in palavra {
    print(char);
}
```

---

## Structs

### Definição

```codon
struct Ponto {
    x: int;
    y: int;
}

struct Pessoa {
    nome: string;
    idade: int;
    altura: double;
}
```

### Uso

```codon
function main(): int {
    // Criar struct
    let p: Ponto = new Ponto { x: 10, y: 20 };
    
    // Acessar campos
    print(p.x);  // 10
    print(p.y);  // 20
    
    // Modificar campos
    p.x = 15;
    
    // Struct aninhada
    let pessoa: Pessoa = new Pessoa {
        nome: "João",
        idade: 25,
        altura: 1.75
    };
    
    print(pessoa.nome);
    
    return 0;
}
```

---

## Classes e Objetos

### Definição

```codon
class Animal {
    nome: string;
    idade: int;
    
    constructor(n: string, i: int) {
        this.nome = n;
        this.idade = i;
    }
    
    procedure falar() {
        print(this.nome + " faz barulho");
    }
}
```

### Herança

```codon
class Cachorro extends Animal {
    raca: string;
    
    constructor(n: string, i: int, r: string) {
        super(n, i);
        this.raca = r;
    }
    
    procedure falar() {
        print(this.nome + " late: Au au!");
    }
    
    procedure correr() {
        print(this.nome + " está correndo");
    }
}
```

### Uso

```codon
function main(): int {
    let rex: Cachorro = new Cachorro("Rex", 3, "Labrador");
    
    rex.falar();    // "Rex late: Au au!"
    rex.correr();   // "Rex está correndo"
    
    print(rex.nome);   // "Rex"
    print(rex.raca);   // "Labrador"
    
    return 0;
}
```

---

## Enums

### Definição

```codon
enum Cor {
    Vermelho,
    Verde,
    Azul
}

enum Estado {
    Ativo,
    Inativo,
    Pausado
}
```

### Uso

```codon
function main(): int {
    let cor_favorita: Cor = Cor.Vermelho;
    
    if cor_favorita == Cor.Vermelho {
        print("Cor é vermelha");
    }
    
    let estado: Estado = Estado.Ativo;
    print(estado);  // Imprime valor numérico (0)
    
    return 0;
}
```

---

## Generics (Tipos Genéricos)

### Funções Genéricas

```codon
function primeiro<T>(arr: T[]): T {
    return arr[0];
}

function trocar<T>(a: T, b: T): void {
    let temp: T = a;
    a = b;
    b = temp;
}

function main(): int {
    let nums: int[] = [1, 2, 3];
    let primeiro_num = primeiro<int>(nums);  // 1
    
    let palavras: string[] = ["a", "b", "c"];
    let primeira_palavra = primeiro<string>(palavras);  // "a"
    
    return 0;
}
```

### Classes Genéricas

```codon
class Caixa<T> {
    valor: T;
    
    constructor(v: T) {
        this.valor = v;
    }
    
    function obter(): T {
        return this.valor;
    }
}

function main(): int {
    let caixa_int: Caixa<int> = new Caixa<int>(42);
    print(caixa_int.obter());  // 42
    
    let caixa_str: Caixa<string> = new Caixa<string>("Hello");
    print(caixa_str.obter());  // "Hello"
    
    return 0;
}
```

### Structs Genéricas

```codon
struct Par<T, U> {
    primeiro: T;
    segundo: U;
}

function main(): int {
    let p: Par<int, string> = new Par<int, string> {
        primeiro: 1,
        segundo: "um"
    };
    
    print(p.primeiro);  // 1
    print(p.segundo);   // "um"
    
    return 0;
}
```

---

## Maps (Dicionários)

### Declaração e Uso

```codon
function main(): int {
    // Map de int -> string
    let idades: map<int, string> = new map<int, string>(10);
    
    // Inserir valores
    idades.set(1, "um");
    idades.set(2, "dois");
    idades.set(3, "três");
    
    // Obter valores
    let valor = idades.get(2);  // "dois"
    print(valor);
    
    // Tamanho
    print(idades.size());  // 3
    
    return 0;
}
```

### Map com String como Chave

```codon
function main(): int {
    let telefones: map<string, int> = new map<string, int>(5);
    
    telefones.set("João", 123456);
    telefones.set("Maria", 789012);
    
    let tel_joao = telefones.get("João");
    print(tel_joao);  // 123456
    
    return 0;
}
```

### Map com Tipos Complexos

```codon
function main(): int {
    // bool -> int
    let flags: map<bool, int> = new map<bool, int>(2);
    flags.set(true, 1);
    flags.set(false, 0);
    
    // double -> string
    let notas: map<double, string> = new map<double, string>(5);
    notas.set(9.5, "Excelente");
    notas.set(7.0, "Bom");
    
    return 0;
}
```

---

## Funções Nativas

### Entrada/Saída

```codon
print(valor);           // Imprime valor (int, double, string, bool)
let entrada = input();  // Lê string do stdin
```

### String

```codon
let tamanho = strlen(str);  // Retorna tamanho da string
```

### Matemática

```codon
let raiz = sqrt(16.0);     // Raiz quadrada: 4.0
let potencia = pow(2.0, 3.0);  // Potência: 8.0
```

### Conversão de Tipos

```codon
let s = int_to_string(42);      // "42"
let i = string_to_int("123");   // 123
let d = string_to_double("3.14"); // 3.14
```

---

## Exemplos Completos

### 1. Calculadora Simples

```codon
function somar(a: double, b: double): double {
    return a + b;
}

function subtrair(a: double, b: double): double {
    return a - b;
}

function multiplicar(a: double, b: double): double {
    return a * b;
}

function dividir(a: double, b: double): double {
    if b == 0.0 {
        print("Erro: divisão por zero");
        return 0.0;
    }
    return a / b;
}

function main(): int {
    let x = 10.0;
    let y = 3.0;
    
    print("Soma: ");
    print(somar(x, y));
    
    print("Subtracao: ");
    print(subtrair(x, y));
    
    print("Multiplicacao: ");
    print(multiplicar(x, y));
    
    print("Divisao: ");
    print(dividir(x, y));
    
    return 0;
}
```

### 2. Gerenciador de Estudantes

```codon
struct Estudante {
    nome: string;
    matricula: int;
    nota: double;
}

function aprovado(e: Estudante): bool {
    return e.nota >= 7.0;
}

function main(): int {
    let alunos: Estudante[] = [
        new Estudante { nome: "Ana", matricula: 1001, nota: 8.5 },
        new Estudante { nome: "João", matricula: 1002, nota: 6.0 },
        new Estudante { nome: "Maria", matricula: 1003, nota: 9.2 }
    ];
    
    for aluno in alunos {
        print(aluno.nome);
        if aprovado(aluno) {
            print("Aprovado");
        } else {
            print("Reprovado");
        }
    }
    
    return 0;
}
```

### 3. Sistema com Classes

```codon
class Conta {
    titular: string;
    saldo: double;
    
    constructor(t: string, s: double) {
        this.titular = t;
        this.saldo = s;
    }
    
    procedure depositar(valor: double) {
        this.saldo = this.saldo + valor;
        print("Depositado: ");
        print(valor);
    }
    
    procedure sacar(valor: double) {
        if valor <= this.saldo {
            this.saldo = this.saldo - valor;
            print("Sacado: ");
            print(valor);
        } else {
            print("Saldo insuficiente");
        }
    }
    
    function obter_saldo(): double {
        return this.saldo;
    }
}

function main(): int {
    let conta: Conta = new Conta("João Silva", 1000.0);
    
    conta.depositar(500.0);
    conta.sacar(200.0);
    
    print("Saldo final: ");
    print(conta.obter_saldo());
    
    return 0;
}
```

### 4. Algoritmo com Generics

```codon
function maximo<T>(a: T, b: T): T {
    if a > b {
        return a;
    }
    return b;
}

function main(): int {
    let maior_int = maximo<int>(10, 20);
    print(maior_int);  // 20
    
    let maior_double = maximo<double>(3.14, 2.71);
    print(maior_double);  // 3.14
    
    return 0;
}
```

---

## Convenções e Boas Práticas

1. **Nomes de variáveis e funções**: `snake_case` ou `camelCase`
2. **Nomes de classes e structs**: `PascalCase`
3. **Nomes de constantes**: `UPPER_CASE`
4. **Indentação**: 4 espaços ou 1 tab
5. **Sempre use ponto e vírgula** após declarações
6. **Use tipos explícitos** para melhor legibilidade
7. **Comente código complexo**

---

## Limitações Conhecidas

- Não há coleta de lixo automática (garbage collection)
- Arrays têm tamanho fixo após criação
- Strings são imutáveis
- Não há sobrecarga de funções (exceto via generics)
- Não há exceções (error handling manual)

---

## Próximos Passos

Para mais exemplos, veja a pasta `examples/` do projeto:
- `examples/basicos/` - Exemplos introdutórios
- `examples/intermediarios/` - Arrays, classes, structs
- `examples/avancados/` - Generics, enums, programas complexos

Para dúvidas ou contribuições, consulte o repositório:
https://github.com/leticia-pontes/codon
