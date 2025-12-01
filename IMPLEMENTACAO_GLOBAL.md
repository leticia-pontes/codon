# Instalação Global do Codon - Resumo da Implementação

## O que foi feito

Implementamos um sistema completo de instalação que permite usar o comando `codon` de **qualquer diretório**, sem precisar estar na raiz do projeto.

## Arquivos criados/modificados

### 1. `setup.py` (NOVO)
- Arquivo de configuração para instalar o Codon como pacote Python
- Define o entry point `codon` que aponta para `codon:main`
- Permite instalação via `pip install -e .`

### 2. `codon/__init__.py` (NOVO)
- Módulo Python com a função `main()` que serve como entry point
- Converte caminhos relativos para absolutos automaticamente
- Permite executar arquivos `.cd` de qualquer diretório

### 3. `install.bat` (NOVO - Windows)
- Script automático de instalação para Windows
- Verifica se Python está instalado
- Cria venv (ou usa existente)
- Instala dependências
- Instala o comando `codon` globalmente

### 4. `install.sh` (NOVO - Linux/macOS)
- Script automático de instalação para Linux/macOS
- Mesma funcionalidade do `install.bat`
- Define permissões de execução automaticamente

### 5. `README.md` (ATUALIZADO)
- Seção "Instalação Automática" com instruções simplificadas
- Seção "Manual de Utilização" mostrando uso do comando `codon`
- Seção "Perguntas Frequentes" com dúvidas comuns
- Atualizado o sumário com novas seções

### 6. `QUICK_START.md` (NOVO)
- Guia rápido de uso pós-instalação
- Exemplos práticos de uso
- Dicas de configuração de alias permanente

### 7. `.gitignore` (ATUALIZADO)
- Adicionados: `*.egg-info/`, `dist/`, `build/`, `*.ll`, `*.bc`, `*.o`
- Reorganizado para melhor clareza

## Como funciona

### Antes (problemático):
```bash
cd C:\Users\letic\Desktop\Unimar\Compiladores\codon
python codon.py run examples/basicos/hello_world.cd  # Só funcionava na raiz
```

### Agora (solução):
```bash
# Uma vez: executar instalação
cd C:\Users\letic\Desktop\Unimar\Compiladores\codon
.\install.bat  # Windows
# OU
./install.sh   # Linux/macOS

# Ativar venv (uma vez por sessão do terminal)
.\.venv\Scripts\activate  # Windows
# OU
source .venv/bin/activate  # Linux/macOS

# Usar de qualquer lugar!
cd C:\
codon run Users\letic\Desktop\Unimar\Compiladores\codon\examples\basicos\hello_world.cd

cd ~/meus_projetos
codon run ./meu_programa.cd
codon build ../outro_projeto/teste.cd > output.ll
```

## Vantagens

✅ **Uso global:** Execute `codon` de qualquer diretório  
✅ **Caminhos flexíveis:** Suporta caminhos relativos e absolutos  
✅ **Instalação simples:** Um único comando (`.\install.bat` ou `./install.sh`)  
✅ **Sem necessidade de configuração manual:** Tudo automatizado  
✅ **Portável:** Funciona em Windows, Linux e macOS  
✅ **Modo desenvolvedor:** `pip install -e .` permite editar código sem reinstalar

## Testes realizados

✅ Executar de outro diretório com caminho absoluto  
✅ Executar de outro diretório com caminho relativo  
✅ Comando `build` gerando LLVM IR  
✅ Instalação via `install.bat` no Windows  
✅ Verificação de venv existente  

## Próximos passos opcionais

- [ ] Criar executável standalone com PyInstaller (elimina necessidade de venv)
- [ ] Adicionar ao PATH permanentemente via script
- [ ] Criar instalador MSI/DEB para distribuição
- [ ] Publicar no PyPI para instalação via `pip install codon-compiler`

## Estrutura de arquivos adicionada

```
codon/
├── setup.py              # Configuração pip
├── install.bat           # Instalador Windows
├── install.sh            # Instalador Linux/macOS
├── QUICK_START.md        # Guia rápido
├── codon/
│   └── __init__.py       # Entry point do comando
├── .gitignore            # Atualizado
└── README.md             # Atualizado
```
