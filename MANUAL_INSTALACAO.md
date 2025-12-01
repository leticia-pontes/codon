# Manual de Instalação - Compilador Codon

## Para Leigos (Passo a Passo Completo)

Este manual explica **do zero** como instalar e usar o compilador Codon, mesmo que você nunca tenha programado antes.

---

## Sumário

* [Pré-requisitos](#pré-requisitos)
* [Instalação no Windows](#instalação-no-windows)
* [Instalação no Linux](#instalação-no-linux)
* [Instalação no macOS](#instalação-no-macos)
* [Verificação da Instalação](#verificação-da-instalação)
* [Primeiro Programa](#primeiro-programa)
* [Solução de Problemas](#solução-de-problemas)

---

## Pré-requisitos

Você precisa ter **Python 3.10 ou superior** instalado no seu computador.

### Como verificar se Python está instalado

**Windows:**
1. Pressione `Win + R`
2. Digite `cmd` e pressione Enter
3. Digite: `python --version`
4. Se aparecer algo como `Python 3.12.x`, você já tem Python!

**Linux/macOS:**
1. Abra o Terminal
2. Digite: `python3 --version`
3. Se aparecer algo como `Python 3.12.x`, você já tem Python!

### Se Python NÃO estiver instalado:

**Windows:**
1. Acesse: https://www.python.org/downloads/
2. Clique em "Download Python 3.12.x" (ou versão mais recente)
3. Execute o instalador baixado
4. ⚠️ **IMPORTANTE**: Marque a opção "Add Python to PATH"
5. Clique em "Install Now"
6. Aguarde a instalação concluir

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
1. Instale o Homebrew (se não tiver): https://brew.sh/
2. No Terminal:
```bash
brew install python@3.12
```

---

## Instalação no Windows

### Passo 1: Baixar o Projeto

**Opção A: Com Git (recomendado)**

1. Instale o Git: https://git-scm.com/download/win
2. Abra o PowerShell (procure por "PowerShell" no menu Iniciar)
3. Navegue até onde quer salvar o projeto. Por exemplo:
   ```powershell
   cd C:\Users\SeuNome\Documents
   ```
4. Clone o repositório:
   ```powershell
   git clone https://github.com/leticia-pontes/codon.git
   ```

**Opção B: Download Manual**

1. Acesse: https://github.com/leticia-pontes/codon
2. Clique no botão verde "Code" → "Download ZIP"
3. Extraia o arquivo ZIP em uma pasta (ex: `C:\Users\SeuNome\Documents\codon`)

### Passo 2: Executar o Instalador Automático

1. Abra o PowerShell como **Administrador**
   - Clique com botão direito no ícone do PowerShell
   - Escolha "Executar como administrador"

2. Navegue até a pasta do Codon:
   ```powershell
   cd C:\Users\SeuNome\Documents\codon
   ```

3. Execute o instalador:
   ```powershell
   .\install.bat
   ```

4. O script vai:
   - ✅ Criar um ambiente virtual Python
   - ✅ Instalar dependências (llvmlite)
   - ✅ Configurar o comando `codon`
   - ✅ Exibir mensagem de sucesso

### Passo 3: Ativar o Ambiente Virtual

**Você precisa fazer isso APENAS UMA VEZ por sessão do terminal.**

```powershell
.\.venv\Scripts\activate
```

Você verá `(.venv)` aparecer no início da linha do terminal. Isso significa que está ativado!

### Passo 4: Testar a Instalação

```powershell
codon run examples\basicos\hello_world.cd
```

Se aparecer "Hello, Codon!", está tudo funcionando! 🎉

---

## Instalação no Linux

### Passo 1: Baixar o Projeto

```bash
# Navegue até sua pasta home
cd ~

# Clone o repositório
git clone https://github.com/leticia-pontes/codon.git

# Entre na pasta
cd codon
```

### Passo 2: Executar o Instalador Automático

```bash
# Torne o script executável
chmod +x install.sh

# Execute o instalador
./install.sh
```

O script vai instalar tudo automaticamente.

### Passo 3: Ativar o Ambiente Virtual

```bash
source .venv/bin/activate
```

Você verá `(.venv)` aparecer no prompt.

### Passo 4: Testar a Instalação

```bash
codon run examples/basicos/hello_world.cd
```

---

## Instalação no macOS

### Passo 1: Instalar Dependências

```bash
# Instale o Homebrew (se não tiver)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instale Python
brew install python@3.12
```

### Passo 2: Baixar o Projeto

```bash
cd ~
git clone https://github.com/leticia-pontes/codon.git
cd codon
```

### Passo 3: Executar o Instalador

```bash
chmod +x install.sh
./install.sh
```

### Passo 4: Ativar o Ambiente Virtual

```bash
source .venv/bin/activate
```

### Passo 5: Testar

```bash
codon run examples/basicos/hello_world.cd
```

---

## Verificação da Instalação

### Verificar se comando `codon` está disponível

Com o ambiente virtual ativado, execute:

```bash
codon run
```

Deve aparecer:
```
Uso:
  codon run <arquivo.cd>     # Compila e executa
  codon build <arquivo.cd>   # Apenas compila (imprime LLVM IR)
  codon build <arquivo.cd> --quiet  # Sem mensagens informativas
```

### Executar os Testes

Para ter certeza que tudo funciona:

**Windows:**
```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\scripts\run_all_tests.ps1
```

**Linux/macOS:**
```bash
./scripts/run_all_tests.sh
```

Você deve ver:
- ✅ Vários testes unitários passando
- ✅ Exemplos sendo compilados com sucesso
- ✅ Resumo no final: "47 exemplos OK, 0 erros"

---

## Primeiro Programa

### Passo 1: Criar um Arquivo

Crie um arquivo chamado `meu_primeiro_programa.cd` com o seguinte conteúdo:

```codon
function main(): int {
    print("Meu primeiro programa em Codon!");
    
    let x: int = 10;
    let y: int = 20;
    let soma: int = x + y;
    
    print("A soma de ");
    print(x);
    print(" e ");
    print(y);
    print(" é ");
    print(soma);
    
    return 0;
}
```

### Passo 2: Executar

**Windows:**
```powershell
# Certifique-se que o venv está ativado
.\.venv\Scripts\activate

# Execute
codon run meu_primeiro_programa.cd
```

**Linux/macOS:**
```bash
# Certifique-se que o venv está ativado
source .venv/bin/activate

# Execute
codon run meu_primeiro_programa.cd
```

### Passo 3: Ver a Saída

Você deve ver:
```
[INFO] Compilando e executando: meu_primeiro_programa.cd
[INFO] Caminho: C:\...\meu_primeiro_programa.cd

Meu primeiro programa em Codon!
A soma de 10 e 20 é 30
```

---

## Solução de Problemas

### Erro: "Python não encontrado"

**Solução:** Instale o Python 3.10+ (veja seção Pré-requisitos acima).

### Erro: "pip não encontrado"

**Windows:**
```powershell
python -m ensurepip --upgrade
```

**Linux:**
```bash
sudo apt install python3-pip
```

### Erro: "llvmlite não pôde ser instalado"

**Linux:** Instale dependências de build:
```bash
sudo apt install build-essential python3-dev
```

**macOS:**
```bash
xcode-select --install
```

### Erro: "codon: comando não encontrado"

**Solução:** Você esqueceu de ativar o ambiente virtual!

**Windows:**
```powershell
.\.venv\Scripts\activate
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### Erro: "Acesso negado" no Windows

**Solução:** Execute o PowerShell como Administrador.

### O ambiente virtual não ativa

**Windows:** Se o PowerShell bloquear scripts:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Erro de encoding/caracteres estranhos

**Solução:** Certifique-se que seu arquivo `.cd` está salvo em UTF-8.

No VS Code: Canto inferior direito → Clique em "UTF-8" → Salvar com encoding → UTF-8.

---

## Desinstalação

Se quiser remover o Codon:

1. Desative o ambiente virtual (se estiver ativo):
   ```bash
   deactivate
   ```

2. Delete a pasta do projeto:
   **Windows:**
   ```powershell
   Remove-Item -Recurse -Force C:\Users\SeuNome\Documents\codon
   ```
   
   **Linux/macOS:**
   ```bash
   rm -rf ~/codon
   ```

---

## Próximos Passos

Agora que você instalou com sucesso:

1. 📖 Leia o **Manual de Utilização** (`MANUAL_UTILIZACAO.md`) para aprender a sintaxe
2. 📂 Explore os exemplos em `examples/basicos/`
3. 💻 Comece a escrever seus próprios programas!
4. 🎓 Consulte a gramática formal em `docs/gramatica-formal-atualizada.md`

---

## Suporte

- **Repositório:** https://github.com/leticia-pontes/codon
- **Issues:** https://github.com/leticia-pontes/codon/issues
- **Documentação completa:** Veja a pasta `docs/`

Boa programação! 🚀
