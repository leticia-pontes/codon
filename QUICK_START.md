# Guia Rápido - Uso do Codon

## Após instalação com `install.bat` ou `install.sh`

### 1. Ative o ambiente virtual (uma vez por sessão)

**Windows:**
```powershell
cd C:\Users\letic\Desktop\Unimar\Compiladores\codon
.\.venv\Scripts\activate
```

**Linux/macOS:**
```bash
cd ~/codon
source .venv/bin/activate
```

### 2. Use `codon` de qualquer lugar

Agora você pode navegar para qualquer diretório e executar programas `.cd`:

```bash
# Ir para outro diretório
cd ~/meus_projetos
# ou
cd C:\Users\letic\Documents

# Criar um programa simples
echo 'function main(): int { print("Teste!"); return 0; }' > teste.cd

# Executar de qualquer lugar
codon run teste.cd
codon run ./meus_codigos/programa.cd
codon run C:\caminho\completo\para\arquivo.cd

# Compilar para LLVM IR (mostra mensagens informativas)
codon build teste.cd

# Compilar sem mensagens (ideal para salvar em arquivo)
codon build teste.cd --quiet > teste.ll
```

### 3. Exemplos práticos

```bash
# Do seu diretório de trabalho atual, executar exemplos do projeto:
codon run C:\Users\letic\Desktop\Unimar\Compiladores\codon\examples\basicos\hello_world.cd
codon run ~/codon/examples/intermediarios/classes.cd

# Criar e executar seu próprio código:
mkdir meu_projeto
cd meu_projeto
echo 'function main(): int {
  let x: int = 42;
  print(x);
  return 0;
}' > programa.cd

codon run programa.cd
```

### 4. Desativar ambiente virtual

```bash
deactivate
```

## Dica: Alias permanente (opcional)

Para não precisar ativar o venv toda vez:

**Linux/macOS** (adicionar ao `~/.bashrc` ou `~/.zshrc`):
```bash
alias codon='~/codon/.venv/bin/codon'
```

**Windows** (criar `codon.bat` em uma pasta no PATH, ex: `C:\Scripts`):
```batch
@echo off
C:\Users\letic\Desktop\Unimar\Compiladores\codon\.venv\Scripts\codon.exe %*
```

Adicione `C:\Scripts` ao PATH do Windows e reinicie o terminal.
