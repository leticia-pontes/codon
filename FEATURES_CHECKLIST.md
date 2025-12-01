## Implementados ✅

- Tipos primitivos: `int`, `double`, `bool`, `string`, `void`, `null`.
- Tipos biológicos: `dna`, `rna`, `prot`.
- Funções: declaração, parâmetros, retorno, chamadas, recursão.
- **Generics completo**:
  - Funções genéricas: `function nome<T>(x: T): T { ... }` com chamadas `func<int>(x)`.
  - Classes genéricas: `class Container<T> { ... }` com instanciação `new Container<int>()`.
  - Structs genéricos: `struct Pair<T,U> { ... }` com múltiplos parâmetros de tipo.
  - Monomorphization: instanciação em tempo de compilação para cada tipo usado.
- Classes: declaração, campos, métodos com `self` implícito.
- Structs: declaração e uso como agregados sem métodos.
- Tuples: literais `(a, b, ...)` e acesso por índice `t[i]`.
- Enums: declaração `enum Nome { Membros }` e uso `Enum.Membro`.
- Operadores: aritméticos, relacionais, lógicos, bitwise, range e atribuições (inclui `++`, `--`).
- Controle de fluxo: `if`, `while`, `for`, loop infinito com `break/continue`.
- Foreach: ranges, strings e arrays tipados.
- Strings: escapes, concatenação, comparação, `.length`, `substring`.
- Arrays: `T[]`, `new T[n]`, `a[i]`, `.length`, literal `[1,2,3]`, slicing `a[i..j]`.
- Arrays multidimensionais: `new T[m][n]`, acesso `a[i][j]`, iteração por linhas.
- I/O: `print(...)`, `input()`, `inputInt()`.
- Maps: `map[K, T]` com chaves `int`, `string`, `bool`, `double` e tipos customizados (classes) usando `equals`. Criação `new map[K,T](cap)`, set/get `m[key] = v`, ` x = m[key]` (strings via `strcmp`; classes via método `equals`).

## Não Implementados ❌

- Hash/buckets para maps (há método `hash()` disponível em classes, ainda não utilizado em distribuição por buckets).
- `switch/match`, exceções (`try/catch`), módulos/import, namespaces, packages.
- Lambdas/closures, overload de funções, pattern matching, reflexão, macros, decorators.
- Runtime: gerenciamento de memória (`free`, GC, RAII/RC), I/O de arquivos avançado.
