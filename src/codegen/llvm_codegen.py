from llvmlite import ir
from typing import Dict, Optional, Tuple
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao, InstrucaoIf,
    InstrucaoLoopWhile, InstrucaoLoopFor, InstrucaoImpressao,
    InstrucaoRetorno, ExpressaoBinaria, ExpressaoUnaria, Literal,
    Variavel, ChamadaFuncao, ASTNode, CriacaoArray, AcessoArray,
    InstrucaoBreak, InstrucaoContinue, LiteralArray, InstrucaoLoopInfinito,
    DeclaracaoClasse, CriacaoClasse, AcessoCampo
)


class LLVMCodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="module")
        self.builder = None
        self.func = None
        self.symbols: Dict[str, ir.AllocaInstr] = {}  # variáveis locais
        # Pilha de loops: [(continue_block, break_block), ...]
        self.loop_stack: list[Tuple[ir.Block, ir.Block]] = []
        # Mapeamento de classes: nome -> (struct_type, {campo: index})
        self.classes: Dict[str, Tuple[ir.LiteralStructType, Dict[str, int]]] = {}

    # -------------------------
    # Entrada: gerar código LLVM IR para o programa
    # -------------------------
    def generate(self, program: Programa) -> str:
        # Separa declarações de funções, classes e instruções
        classes = [d for d in program.declaracoes if isinstance(d, DeclaracaoClasse)]
        funcoes = [d for d in program.declaracoes if isinstance(d, DeclaracaoFuncao)]
        instrucoes = [d for d in program.declaracoes if not isinstance(d, (DeclaracaoFuncao, DeclaracaoClasse))]
        
        # Registra todas as classes primeiro
        for class_decl in classes:
            self._register_class(class_decl)
        
        # Verifica se existe uma função main() definida pelo usuário
        user_main = next((f for f in funcoes if f.nome == "main"), None)
        
        # Gera todas as funções
        for func_decl in funcoes:
            self._gen_function(func_decl)
        
        # Se não há main() definida, cria wrapper main()
        if user_main is None:
            main_type = ir.FunctionType(ir.IntType(32), [])
            main_func = ir.Function(self.module, main_type, name="main")
            block = main_func.append_basic_block("entry")
            self.builder = ir.IRBuilder(block)
            self.func = main_func
            
            # Gera código para instruções no escopo global
            for decl in instrucoes:
                self._gen_stmt(decl)
            
            # Retorno padrão
            if self.builder.block.is_terminated is False:
                self.builder.ret(ir.Constant(ir.IntType(32), 0))
        
        return str(self.module)

    # -------------------------
    # Strings
    # -------------------------
    def _gen_string(self, value: str):
        """
        Cria uma string constante no LLVM e retorna um ponteiro para ela.
        Suporta UTF-8 corretamente.
        """
        # Processa sequências de escape (\n, \t, \", \\ etc.) antes de codificar
        value = self._unescape_string(value)
        # Codifica em UTF-8 e adiciona terminador nulo '\0'
        str_bytes = value.encode("utf-8") + b"\0"
        # Converte bytes para lista de inteiros para LLVM
        str_ints = list(str_bytes)
        str_type = ir.ArrayType(ir.IntType(8), len(str_ints))

        # Cria global string
        global_str = ir.GlobalVariable(self.module, str_type, name=f"str{len(self.module.globals)}")
        global_str.linkage = 'internal'
        global_str.global_constant = True
        global_str.initializer = ir.Constant(str_type, str_ints)

        # Retorna ponteiro para o primeiro elemento (i8*) via GEP
        zero = ir.Constant(ir.IntType(32), 0)
        return self.builder.gep(global_str, [zero, zero], inbounds=True)

    def _unescape_string(self, s: str) -> str:
        """
        Converte sequências de escape comuns em seus caracteres reais.
        Suporta: \n, \r, \t, \", \\', \\, \0
        """
        out = []
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch == '\\' and i + 1 < n:
                nxt = s[i+1]
                if nxt == 'n': out.append('\n')
                elif nxt == 'r': out.append('\r')
                elif nxt == 't': out.append('\t')
                elif nxt == '"': out.append('"')
                elif nxt == "'": out.append("'")
                elif nxt == '0': out.append('\0')
                else:
                    # fallback: mantém o segundo caractere literalmente
                    out.append(nxt)
                i += 2
            else:
                out.append(ch)
                i += 1
        return ''.join(out)

    # -------------------------
    # Statements
    # -------------------------
    def _gen_stmt(self, node: ASTNode):
        if node is None:
            return

        if isinstance(node, InstrucaoAtribuicao):
            # Atribuição para variável simples
            if isinstance(node.alvo, Variavel):
                name = node.alvo.nome
                
                # Operadores compostos: +=, -=, etc.
                if node.operador in ('+=', '-=', '*=', '/='):
                    if name not in self.symbols:
                        raise NameError(f"Variável '{name}' não declarada para operador composto")
                    
                    # Load do valor atual
                    current_val = self.builder.load(self.symbols[name], name)
                    rhs_val = self._gen_expr(node.valor)
                    
                    # Valida tipos: ambos devem ser numéricos (IntType ou DoubleType)
                    if isinstance(current_val.type, ir.PointerType) or isinstance(rhs_val.type, ir.PointerType):
                        raise TypeError(f"Operador composto '{node.operador}' não suportado entre tipos {current_val.type} e {rhs_val.type}")
                    
                    # Realiza a operação
                    if node.operador == '+=':
                        new_val = self.builder.add(current_val, rhs_val)
                    elif node.operador == '-=':
                        new_val = self.builder.sub(current_val, rhs_val)
                    elif node.operador == '*=':
                        new_val = self.builder.mul(current_val, rhs_val)
                    elif node.operador == '/=':
                        new_val = self.builder.sdiv(current_val, rhs_val)
                    
                    self.builder.store(new_val, self.symbols[name])
                else:
                    # Atribuição simples: =
                    val = self._gen_expr(node.valor)
                    if name not in self.symbols:
                        alloca = self.builder.alloca(val.type, name=name)
                        self.symbols[name] = alloca
                    else:
                        # Se o valor é null (i8*) e a variável é de outro tipo de ponteiro, faz cast
                        target_type = self.symbols[name].type.pointee
                        if isinstance(val.type, ir.PointerType) and isinstance(target_type, ir.PointerType):
                            if val.type != target_type:
                                val = self.builder.bitcast(val, target_type)
                    self.builder.store(val, self.symbols[name])
            # Atribuição para elemento de array: alvo[indice] = valor
            elif isinstance(node.alvo, AcessoArray):
                val = self._gen_expr(node.valor)
                base_ptr = self._gen_expr(node.alvo.alvo)  # deve ser i32*
                index_val = self._gen_expr(node.alvo.indice)
                if not isinstance(index_val.type, ir.IntType):
                    # força índice para i32
                    index_val = self.builder.ptrtoint(index_val, ir.IntType(32)) if isinstance(index_val.type, ir.PointerType) else self.builder.trunc(index_val, ir.IntType(32))
                elem_ptr = self.builder.gep(base_ptr, [index_val])
                self.builder.store(val, elem_ptr)
            else:
                raise NotImplementedError("Atribuição para alvo não suportado")

        elif isinstance(node, InstrucaoImpressao):
            printf = self._get_printf()
            # Imprime argumentos com espaço entre eles, e quebra de linha ao final
            for idx, expr in enumerate(node.expressoes or []):
                if idx > 0:
                    self.builder.call(printf, [self._gen_string(" ")])
                val = None
                # Se literal string, imprime diretamente
                if isinstance(expr, Literal) and isinstance(expr.valor, str):
                    fmt = self._gen_string("%s")
                    str_ptr = self._gen_string(expr.valor)
                    self.builder.call(printf, [fmt, str_ptr])
                    continue
                # Gera valor
                val = self._gen_expr(expr)
                # Seleciona formato por tipo
                if isinstance(val.type, ir.PointerType) and val.type.pointee == ir.IntType(8):
                    fmt = self._gen_string("%s")
                    self.builder.call(printf, [fmt, val])
                elif isinstance(val.type, ir.DoubleType):
                    fmt = self._gen_string("%f")
                    self.builder.call(printf, [fmt, val])
                elif isinstance(val.type, ir.IntType) and val.type.width == 1:
                    fmt = self._gen_string("%d")
                    self.builder.call(printf, [fmt, val])
                else:
                    fmt = self._gen_string("%d")
                    self.builder.call(printf, [fmt, val])
            # Nova linha ao final
            self.builder.call(printf, [self._gen_string("\n")])

        elif isinstance(node, InstrucaoRetorno):
            if getattr(node, "expressao", None):
                val = self._gen_expr(node.expressao)
            else:
                val = ir.Constant(ir.IntType(32), 0)
            self.builder.ret(val)

        elif isinstance(node, InstrucaoIf):
            self._gen_if(node)

        elif isinstance(node, InstrucaoLoopWhile):
            self._gen_while(node)

        elif isinstance(node, InstrucaoLoopInfinito):
            self._gen_loop_infinito(node)

        elif isinstance(node, InstrucaoLoopFor):
            self._gen_for(node)

        elif isinstance(node, DeclaracaoFuncao):
            self._gen_function(node)

        elif isinstance(node, InstrucaoBreak):
            if not self.loop_stack:
                raise RuntimeError("'break' fora de um loop")
            _, break_block = self.loop_stack[-1]
            self.builder.branch(break_block)

        elif isinstance(node, InstrucaoContinue):
            if not self.loop_stack:
                raise RuntimeError("'continue' fora de um loop")
            continue_block, _ = self.loop_stack[-1]
            self.builder.branch(continue_block)

        # Expressão usada como instrução (ex.: chamada de função sem uso do retorno)
        elif isinstance(node, ChamadaFuncao):
            _ = self._gen_expr(node)

        # Expressão unária usada como instrução (ex.: i++, i--)
        elif isinstance(node, ExpressaoUnaria):
            _ = self._gen_expr(node)

    # -------------------------
    # Expressões
    # -------------------------
    def _gen_expr(self, expr: ASTNode):
        if isinstance(expr, Literal):
            if isinstance(expr.valor, int):
                return ir.Constant(ir.IntType(32), expr.valor)
            elif isinstance(expr.valor, float):
                return ir.Constant(ir.DoubleType(), expr.valor)
            elif isinstance(expr.valor, str):
                # string ou char
                return self._gen_string(expr.valor)
            elif isinstance(expr.valor, bool):
                # true -> 1, false -> 0
                return ir.Constant(ir.IntType(1), int(expr.valor))
            elif expr.valor is None:
                # null pointer
                return ir.Constant(ir.IntType(8).as_pointer(), None)
            else:
                raise NotImplementedError(f"Literal não suportado: {type(expr.valor)}")

        elif isinstance(expr, Variavel):
            ptr = self.symbols.get(expr.nome)
            if ptr is None:
                raise NameError(f"Variável '{expr.nome}' não declarada")
            return self.builder.load(ptr, expr.nome)

        elif isinstance(expr, ExpressaoBinaria):
            # Gera operandos
            lhs = self._gen_expr(expr.esquerda)
            rhs = self._gen_expr(expr.direita)
            
            # Normaliza tipos: se um é double e outro int, converte int para double
            if isinstance(lhs.type, ir.DoubleType) and isinstance(rhs.type, ir.IntType):
                rhs = self.builder.sitofp(rhs, ir.DoubleType())
            elif isinstance(rhs.type, ir.DoubleType) and isinstance(lhs.type, ir.IntType):
                lhs = self.builder.sitofp(lhs, ir.DoubleType())
            
            op = expr.operador

            if op == '+':
                # Concatenação de strings / biológicos (todos i8*)
                if isinstance(lhs.type, ir.PointerType) and isinstance(rhs.type, ir.PointerType) and \
                   isinstance(lhs.type.pointee, ir.IntType) and lhs.type.pointee.width == 8 and \
                   isinstance(rhs.type.pointee, ir.IntType) and rhs.type.pointee.width == 8:
                    return self._concat_strings(lhs, rhs)
                if isinstance(lhs.type, ir.DoubleType):
                    return self.builder.fadd(lhs, rhs)
                return self.builder.add(lhs, rhs)
            elif op == "-":
                if isinstance(lhs.type, ir.DoubleType):
                    return self.builder.fsub(lhs, rhs)
                return self.builder.sub(lhs, rhs)
            elif op == "*":
                if isinstance(lhs.type, ir.DoubleType):
                    return self.builder.fmul(lhs, rhs)
                return self.builder.mul(lhs, rhs)
            elif op == "/":
                if isinstance(lhs.type, ir.DoubleType):
                    return self.builder.fdiv(lhs, rhs)
                return self.builder.sdiv(lhs, rhs)
            elif op == "%":
                if isinstance(lhs.type, ir.DoubleType):
                    return self.builder.frem(lhs, rhs)
                return self.builder.srem(lhs, rhs)
            elif op in ("==", "!=", "<", "<=", ">", ">="):
                # Detecta se é comparação de strings, float ou inteira
                if isinstance(lhs.type, ir.PointerType) and lhs.type.pointee == ir.IntType(8):
                    # Comparação de strings usando strcmp
                    if op in ("==", "!="):
                        strcmp_result = self._call_strcmp(lhs, rhs)
                        # strcmp retorna 0 se iguais
                        if op == "==":
                            return self.builder.icmp_signed("==", strcmp_result, ir.Constant(ir.IntType(32), 0))
                        else:  # !=
                            return self.builder.icmp_signed("!=", strcmp_result, ir.Constant(ir.IntType(32), 0))
                    else:
                        # Comparações <, <=, >, >= também com strcmp
                        strcmp_result = self._call_strcmp(lhs, rhs)
                        cmp_map = {"<": "<", "<=": "<=", ">": ">", ">=": ">="}
                        return self.builder.icmp_signed(cmp_map[op], strcmp_result, ir.Constant(ir.IntType(32), 0))
                elif isinstance(lhs.type, ir.DoubleType):
                    fcmp_map = {
                        "==": "==", "!=": "!=", "<": "<", "<=": "<=",
                        ">": ">", ">=": ">="
                    }
                    return self.builder.fcmp_ordered(fcmp_map[op], lhs, rhs)
                else:
                    cmp_map = {
                        "==": "==", "!=": "!=", "<": "<", "<=": "<=",
                        ">": ">", ">=": ">="
                    }
                    return self.builder.icmp_signed(cmp_map[op], lhs, rhs)
            elif op == "&&":
                # Short-circuit AND: se lhs é falso, retorna falso sem avaliar rhs
                return self._gen_logical_and(expr.esquerda, expr.direita)
            elif op == "||":
                # Short-circuit OR: se lhs é verdadeiro, retorna verdadeiro sem avaliar rhs
                return self._gen_logical_or(expr.esquerda, expr.direita)
            elif op == "**":
                # Potência usando llvm.pow intrinsic
                return self._gen_power(lhs, rhs)
            elif op == "&":
                # AND bit-a-bit
                return self.builder.and_(lhs, rhs)
            elif op == "|":
                # OR bit-a-bit
                return self.builder.or_(lhs, rhs)
            elif op == "^":
                # XOR bit-a-bit
                return self.builder.xor(lhs, rhs)
            elif op == "<<":
                # Shift left
                return self.builder.shl(lhs, rhs)
            elif op == ">>":
                # Shift right (aritmético)
                return self.builder.ashr(lhs, rhs)
            else:
                raise NotImplementedError(f"Operador '{op}' não suportado")

        elif isinstance(expr, ExpressaoUnaria):
            val = self._gen_expr(expr.direita)
            if expr.operador == "-":
                return self.builder.neg(val)
            elif expr.operador == "!":
                # Negação booleana
                return self.builder.icmp_unsigned("==", val, ir.Constant(val.type, 0))
            elif expr.operador == "~":
                # NOT bit-a-bit (inverte todos os bits)
                return self.builder.not_(val)
            elif expr.operador == "++":
                # Incremento pós-fixado: retorna valor original, incrementa variável
                if isinstance(expr.direita, Variavel):
                    name = expr.direita.nome
                    if name not in self.symbols:
                        raise NameError(f"Variável '{name}' não declarada")
                    # Load valor atual
                    current = self.builder.load(self.symbols[name])
                    # Incrementa
                    incremented = self.builder.add(current, ir.Constant(current.type, 1))
                    # Store de volta
                    self.builder.store(incremented, self.symbols[name])
                    # Retorna valor ANTES do incremento (pós-fixado)
                    return current
                else:
                    raise NotImplementedError("++ só suportado para variáveis")
            elif expr.operador == "--":
                # Decremento pós-fixado: retorna valor original, decrementa variável
                if isinstance(expr.direita, Variavel):
                    name = expr.direita.nome
                    if name not in self.symbols:
                        raise NameError(f"Variável '{name}' não declarada")
                    # Load valor atual
                    current = self.builder.load(self.symbols[name])
                    # Decrementa
                    decremented = self.builder.sub(current, ir.Constant(current.type, 1))
                    # Store de volta
                    self.builder.store(decremented, self.symbols[name])
                    # Retorna valor ANTES do decremento (pós-fixado)
                    return current
                else:
                    raise NotImplementedError("-- só suportado para variáveis")
            else:
                raise NotImplementedError(f"Operador unário '{expr.operador}' não suportado")

        elif isinstance(expr, ChamadaFuncao):
            # suporta funções com Variavel como nome
            fn_name = expr.nome.nome if isinstance(expr.nome, Variavel) else expr.nome
            
            # Verifica se é uma criação de classe
            if fn_name in self.classes:
                # Converte para CriacaoClasse
                criacao = CriacaoClasse(fn_name, expr.argumentos or [])
                return self._gen_expr(criacao)
            
            # Built-ins especiais
            if fn_name == "input":
                return self._builtin_input()
            elif fn_name == "inputInt":
                return self._builtin_input_int()
            elif fn_name == "printInt":
                printf = self._get_printf()
                fmt = self._gen_string("%d")
                val = self._gen_expr(expr.argumentos[0])
                return self.builder.call(printf, [fmt, val])
            elif fn_name == "substring":
                # substring(s, start, end)
                s = self._gen_expr(expr.argumentos[0])
                start = self._gen_expr(expr.argumentos[1])
                end = self._gen_expr(expr.argumentos[2])
                # Garante i64
                start64 = start if (isinstance(start.type, ir.IntType) and start.type.width == 64) else self.builder.sext(start, ir.IntType(64)) if isinstance(start.type, ir.IntType) else self.builder.fptosi(start, ir.IntType(64))
                end64 = end if (isinstance(end.type, ir.IntType) and end.type.width == 64) else self.builder.sext(end, ir.IntType(64)) if isinstance(end.type, ir.IntType) else self.builder.fptosi(end, ir.IntType(64))
                length = self.builder.sub(end64, start64)
                # Aloca length + 1 bytes
                malloc = self._get_malloc()
                one = ir.Constant(ir.IntType(64), 1)
                alloc_size = self.builder.add(length, one)
                dest = self.builder.call(malloc, [alloc_size])  # i8*
                # src = s + start
                src_off = self.builder.gep(s, [self.builder.trunc(start64, ir.IntType(32))])
                # memcpy(dest, src_off, length)
                memcpy = self._get_memcpy()
                _ = self.builder.call(memcpy, [dest, src_off, length])
                # dest[length] = 0
                dest_end = self.builder.gep(dest, [self.builder.trunc(length, ir.IntType(32))])
                self.builder.store(ir.Constant(ir.IntType(8), 0), dest_end)
                return dest
            
            func = self.module.globals.get(fn_name)
            if func is None:
                raise NameError(f"Função '{fn_name}' não declarada")
            args = [self._gen_expr(a) for a in (expr.argumentos or [])]
            return self.builder.call(func, args)

        elif isinstance(expr, CriacaoArray):
            # Cria array de int32 com tamanho dinâmico via malloc
            size_val = self._gen_expr(expr.tamanho)
            # garante i64 para malloc size
            if isinstance(size_val.type, ir.IntType) and size_val.type.width < 64:
                size_i64 = self.builder.sext(size_val, ir.IntType(64))
            elif isinstance(size_val.type, ir.IntType) and size_val.type.width > 64:
                size_i64 = self.builder.trunc(size_val, ir.IntType(64))
            else:
                # convert pointers/doubles de forma simples
                size_i64 = size_val if isinstance(size_val.type, ir.IntType) and size_val.type.width == 64 else self.builder.ptrtoint(size_val, ir.IntType(64)) if isinstance(size_val.type, ir.PointerType) else self.builder.fptosi(size_val, ir.IntType(64))

            # bytes = 8(header length) + size * 4
            elem_size = ir.Constant(ir.IntType(64), 4)
            data_bytes = self.builder.mul(size_i64, elem_size)
            header_bytes = ir.Constant(ir.IntType(64), 8)
            total_bytes = self.builder.add(header_bytes, data_bytes)

            malloc = self._get_malloc()
            raw_ptr = self.builder.call(malloc, [total_bytes])  # i8*

            # Salva length no header (i64)
            len_ptr = self.builder.bitcast(raw_ptr, ir.IntType(64).as_pointer())
            self.builder.store(size_i64, len_ptr)

            # Data pointer é raw_ptr + 8, como i32*
            data_i8 = self.builder.gep(raw_ptr, [ir.Constant(ir.IntType(32), 8)])
            data_i32 = self.builder.bitcast(data_i8, ir.IntType(32).as_pointer())
            return data_i32

        elif isinstance(expr, AcessoArray):
            base_ptr = self._gen_expr(expr.alvo)  # i32*
            index_val = self._gen_expr(expr.indice)
            if not isinstance(index_val.type, ir.IntType):
                index_val = self.builder.ptrtoint(index_val, ir.IntType(32)) if isinstance(index_val.type, ir.PointerType) else self.builder.trunc(index_val, ir.IntType(32))
            elem_ptr = self.builder.gep(base_ptr, [index_val])
            return self.builder.load(elem_ptr)

        elif isinstance(expr, LiteralArray):
            # Implementa literal de array de int32: [a, b, c]
            elementos = expr.elementos or []
            count = len(elementos)
            malloc = self._get_malloc()
            # bytes = 8(header) + count*4
            total_bytes = ir.Constant(ir.IntType(64), 8 + count * 4)
            raw_ptr = self.builder.call(malloc, [total_bytes])  # i8*
            # grava header length (i64)
            len_ptr = self.builder.bitcast(raw_ptr, ir.IntType(64).as_pointer())
            self.builder.store(ir.Constant(ir.IntType(64), count), len_ptr)
            # data pointer
            data_i8 = self.builder.gep(raw_ptr, [ir.Constant(ir.IntType(32), 8)])
            arr_ptr = self.builder.bitcast(data_i8, ir.IntType(32).as_pointer())
            # Inicializa cada elemento
            for i, e in enumerate(elementos):
                val = self._gen_expr(e)
                # Converte float/bool para i32 se necessário
                if isinstance(val.type, ir.DoubleType):
                    val = self.builder.fptosi(val, ir.IntType(32))
                elif isinstance(val.type, ir.IntType) and val.type.width != 32:
                    val = self.builder.zext(val, ir.IntType(32)) if val.type.width < 32 else self.builder.trunc(val, ir.IntType(32))
                elif isinstance(val.type, ir.PointerType):
                    raise TypeError("Literal de array suporta apenas inteiros por enquanto")
                idx = ir.Constant(ir.IntType(32), i)
                elem_ptr = self.builder.gep(arr_ptr, [idx])
                self.builder.store(val, elem_ptr)
            return arr_ptr

        elif isinstance(expr, CriacaoClasse):
            # Cria instância de classe: aloca struct e inicializa
            if expr.classe not in self.classes:
                raise NameError(f"Classe '{expr.classe}' não declarada")
            
            struct_type, field_map = self.classes[expr.classe]
            malloc = self._get_malloc()
            
            # Calcula tamanho do struct (soma dos tamanhos dos campos)
            # Aproximação: cada campo int/float = 4 bytes, double = 8 bytes, ponteiro = 8 bytes
            total_size = 0
            for field_type in struct_type.elements:
                if isinstance(field_type, ir.IntType):
                    total_size += field_type.width // 8
                elif isinstance(field_type, ir.DoubleType):
                    total_size += 8
                elif isinstance(field_type, ir.FloatType):
                    total_size += 4
                elif isinstance(field_type, ir.PointerType):
                    total_size += 8
                else:
                    total_size += 8  # fallback
            
            size_bytes = ir.Constant(ir.IntType(64), total_size)
            raw_ptr = self.builder.call(malloc, [size_bytes])
            obj_ptr = self.builder.bitcast(raw_ptr, struct_type.as_pointer())
            
            # Inicializa campos com argumentos (assumindo ordem dos campos)
            for idx, arg_expr in enumerate(expr.argumentos or []):
                if idx >= len(field_map):
                    break
                arg_val = self._gen_expr(arg_expr)
                field_ptr = self.builder.gep(obj_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
                self.builder.store(arg_val, field_ptr)
            
            return obj_ptr

        elif isinstance(expr, AcessoCampo):
            # Acesso a campo: obj.campo
            obj_val = self._gen_expr(expr.alvo)

            # Suporte a .length para strings (i8*) e arrays (i32*)
            if expr.campo == 'length':
                # string / biológico: i8*
                if isinstance(obj_val.type, ir.PointerType) and isinstance(obj_val.type.pointee, ir.IntType) and obj_val.type.pointee.width == 8:
                    strlen = self._get_strlen()
                    n = self.builder.call(strlen, [obj_val])  # i64
                    return self.builder.trunc(n, ir.IntType(32))
                # array: i32* com header i64 8 bytes antes
                if isinstance(obj_val.type, ir.PointerType) and isinstance(obj_val.type.pointee, ir.IntType) and obj_val.type.pointee.width == 32:
                    i8ptr = self.builder.bitcast(obj_val, ir.IntType(8).as_pointer())
                    # retrocede 8 bytes
                    base_i8 = self.builder.gep(i8ptr, [ir.Constant(ir.IntType(32), -8)])
                    len_ptr = self.builder.bitcast(base_i8, ir.IntType(64).as_pointer())
                    n = self.builder.load(len_ptr)
                    return self.builder.trunc(n, ir.IntType(32))

            # Determina o tipo da classe do objeto
            if isinstance(obj_val.type, ir.PointerType) and isinstance(obj_val.type.pointee, ir.LiteralStructType):
                struct_type = obj_val.type.pointee
                # Procura a classe correspondente
                class_name = None
                for name, (stype, _) in self.classes.items():
                    if stype == struct_type:
                        class_name = name
                        break
                
                if class_name and class_name in self.classes:
                    _, field_map = self.classes[class_name]
                    if expr.campo in field_map:
                        field_idx = field_map[expr.campo]
                        field_ptr = self.builder.gep(obj_val, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), field_idx)])
                        return self.builder.load(field_ptr)
            
            raise AttributeError(f"Campo '{expr.campo}' não encontrado")

        else:
            raise NotImplementedError(f"Expressão não suportada: {type(expr).__name__}")

    # -------------------------
    # If/Else
    # -------------------------
    def _gen_if(self, node: InstrucaoIf):
        cond_val = self._gen_expr(node.condicao)
        
        # Garante que condição é i1
        if isinstance(cond_val.type, ir.IntType) and cond_val.type.width != 1:
            cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))

        then_block = self.func.append_basic_block("then")
        else_block = self.func.append_basic_block("else")
        end_block = self.func.append_basic_block("ifend")

        self.builder.cbranch(cond_val, then_block, else_block)

        # THEN
        self.builder.position_at_end(then_block)
        for s in node.bloco_if or []:
            self._gen_stmt(s)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)

        # ELSE
        self.builder.position_at_end(else_block)
        for s in node.bloco_else or []:
            self._gen_stmt(s)
        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)

        # Continuar no fim
        self.builder.position_at_end(end_block)

    # -------------------------
    # While
    # -------------------------
    def _gen_while(self, node: InstrucaoLoopWhile):
        start_block = self.func.append_basic_block("while_start")
        body_block = self.func.append_basic_block("while_body")
        end_block = self.func.append_basic_block("while_end")

        self.builder.branch(start_block)

        self.builder.position_at_end(start_block)
        cond_val = self._gen_expr(node.condicao)
        # Garante que condição é i1
        if isinstance(cond_val.type, ir.IntType) and cond_val.type.width != 1:
            cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, body_block, end_block)

        # Empilha info do loop (continue -> start, break -> end)
        self.loop_stack.append((start_block, end_block))

        self.builder.position_at_end(body_block)
        for s in node.corpo or []:
            self._gen_stmt(s)
            # Se break/continue foi chamado, bloco já foi terminado
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(start_block)

        # Desempilha
        self.loop_stack.pop()

        self.builder.position_at_end(end_block)

    # -------------------------
    # Loop Infinito
    # -------------------------
    def _gen_loop_infinito(self, node: InstrucaoLoopInfinito):
        body_block = self.func.append_basic_block("loop_body")
        end_block = self.func.append_basic_block("loop_end")

        self.builder.branch(body_block)

        # Empilha info do loop (continue -> body, break -> end)
        self.loop_stack.append((body_block, end_block))

        self.builder.position_at_end(body_block)
        for s in node.corpo or []:
            self._gen_stmt(s)
            # Se break/continue foi chamado, bloco já foi terminado
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(body_block)  # volta para o início

        # Desempilha
        self.loop_stack.pop()

        self.builder.position_at_end(end_block)

    # -------------------------
    # For (simplificado)
    # -------------------------
    def _gen_for(self, node: InstrucaoLoopFor):
        if getattr(node, "inicializacao", None):
            self._gen_stmt(node.inicializacao)

        start_block = self.func.append_basic_block("for_start")
        body_block = self.func.append_basic_block("for_body")
        step_block = self.func.append_basic_block("for_step")
        end_block = self.func.append_basic_block("for_end")

        self.builder.branch(start_block)

        self.builder.position_at_end(start_block)
        cond_val = self._gen_expr(node.condicao)
        # Garante que condição é i1
        if isinstance(cond_val.type, ir.IntType) and cond_val.type.width != 1:
            cond_val = self.builder.icmp_signed("!=", cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, body_block, end_block)

        # Empilha (continue -> step, break -> end)
        self.loop_stack.append((step_block, end_block))

        self.builder.position_at_end(body_block)
        for s in node.corpo or []:
            self._gen_stmt(s)
            if self.builder.block.is_terminated:
                break
        if not self.builder.block.is_terminated:
            self.builder.branch(step_block)

        # Bloco de incremento
        self.builder.position_at_end(step_block)
        if getattr(node, "passo", None):
            self._gen_stmt(node.passo)
        if not self.builder.block.is_terminated:
            self.builder.branch(start_block)

        # Desempilha
        self.loop_stack.pop()

        self.builder.position_at_end(end_block)

    # -------------------------
    # Funções
    # -------------------------
    def _gen_function(self, decl: DeclaracaoFuncao):
        # Salva contexto atual (main) para restaurar após gerar a função
        prev_builder = self.builder
        prev_func = self.func
        prev_symbols = self.symbols

        try:
            # Mapeia tipos de parâmetros corretamente
            param_types = []
            for pname, ptype in (decl.parametros or []):
                if ptype in ('decimal', 'float', 'double'):
                    param_types.append(ir.DoubleType())
                elif ptype == 'string':
                    param_types.append(ir.IntType(8).as_pointer())
                elif ptype == 'bool':
                    param_types.append(ir.IntType(1))
                else:  # int ou tipo padrão
                    param_types.append(ir.IntType(32))
            
            # Mapeia tipo de retorno
            if decl.tipo_retorno in ('decimal', 'float', 'double'):
                ret_type = ir.DoubleType()
            elif decl.tipo_retorno == 'string':
                ret_type = ir.IntType(8).as_pointer()
            elif decl.tipo_retorno == 'bool':
                ret_type = ir.IntType(1)
            elif decl.tipo_retorno == 'void':
                ret_type = ir.VoidType()
            else:  # int ou tipo padrão
                ret_type = ir.IntType(32)
            func_type = ir.FunctionType(ret_type, param_types)
            func = ir.Function(self.module, func_type, name=decl.nome)
            block = func.append_basic_block("entry")
            self.builder = ir.IRBuilder(block)
            self.func = func

            # Novo escopo de símbolos para a função
            self.symbols = {}
            # Mapear parâmetros de entrada para variáveis locais com mesmo nome
            for idx, (pname, _ptype) in enumerate(decl.parametros or []):
                arg = func.args[idx]
                arg.name = pname
                alloca = self.builder.alloca(arg.type, name=pname)
                self.builder.store(arg, alloca)
                self.symbols[pname] = alloca

            for stmt in decl.corpo or []:
                self._gen_stmt(stmt)

            # Retorno padrão se função não tiver return explícito
            if not self.builder.block.is_terminated:
                if isinstance(ret_type, ir.VoidType):
                    self.builder.ret_void()
                elif isinstance(ret_type, ir.PointerType):
                    # Retorna NULL para ponteiros (ex: string)
                    self.builder.ret(ir.Constant(ret_type, None))
                elif isinstance(ret_type, ir.DoubleType):
                    # Retorna 0.0 para doubles
                    self.builder.ret(ir.Constant(ret_type, 0.0))
                else:
                    # Retorna 0 para inteiros
                    self.builder.ret(ir.Constant(ret_type, 0))
        finally:
            # Restaura contexto do chamador (ex.: main)
            self.builder = prev_builder
            self.func = prev_func
            self.symbols = prev_symbols

    # -------------------------
    # Classes
    # -------------------------
    def _register_class(self, decl: DeclaracaoClasse):
        """
        Registra uma classe criando um struct type e mapeando os campos.
        """
        # Mapeia tipos de campos para LLVM types
        field_types = []
        field_map = {}
        for idx, (campo_nome, campo_tipo) in enumerate(decl.campos):
            field_map[campo_nome] = idx
            if campo_tipo in ('decimal', 'float', 'double'):
                field_types.append(ir.DoubleType())
            elif campo_tipo == 'string':
                field_types.append(ir.IntType(8).as_pointer())
            elif campo_tipo == 'bool':
                field_types.append(ir.IntType(1))
            elif campo_tipo == 'int':
                field_types.append(ir.IntType(32))
            else:
                # Tipo customizado (outra classe)
                if campo_tipo in self.classes:
                    field_types.append(self.classes[campo_tipo][0].as_pointer())
                else:
                    # Por padrão, assume ponteiro genérico
                    field_types.append(ir.IntType(8).as_pointer())
        
        # Cria struct type
        struct_type = ir.LiteralStructType(field_types)
        self.classes[decl.nome] = (struct_type, field_map)

    def _type_from_name(self, type_name: str) -> ir.Type:
        """Helper para mapear nome de tipo para LLVM Type"""
        if type_name in ('decimal', 'float', 'double'):
            return ir.DoubleType()
        elif type_name == 'string':
            return ir.IntType(8).as_pointer()
        elif type_name == 'bool':
            return ir.IntType(1)
        elif type_name == 'int':
            return ir.IntType(32)
        elif type_name in self.classes:
            return self.classes[type_name][0].as_pointer()
        else:
            return ir.IntType(8).as_pointer()

    # -------------------------
    # Helpers
    # -------------------------
    def _get_printf(self):
        printf = self.module.globals.get("printf")
        if printf is None:
            voidptr_ty = ir.IntType(8).as_pointer()
            printf_ty = ir.FunctionType(ir.IntType(32), [voidptr_ty], var_arg=True)
            printf = ir.Function(self.module, printf_ty, name="printf")
        return printf

    def _get_strlen(self):
        strlen = self.module.globals.get("strlen")
        if strlen is None:
            strlen_ty = ir.FunctionType(ir.IntType(64), [ir.IntType(8).as_pointer()])
            strlen = ir.Function(self.module, strlen_ty, name="strlen")
        return strlen

    def _get_malloc(self):
        malloc = self.module.globals.get("malloc")
        if malloc is None:
            malloc_ty = ir.FunctionType(ir.IntType(8).as_pointer(), [ir.IntType(64)])
            malloc = ir.Function(self.module, malloc_ty, name="malloc")
        return malloc

    def _get_strcpy(self):
        strcpy = self.module.globals.get("strcpy")
        if strcpy is None:
            strcpy_ty = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer()]
            )
            strcpy = ir.Function(self.module, strcpy_ty, name="strcpy")
        return strcpy

    def _get_strcat(self):
        strcat = self.module.globals.get("strcat")
        if strcat is None:
            strcat_ty = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer()]
            )
            strcat = ir.Function(self.module, strcat_ty, name="strcat")
        return strcat

    def _get_strcmp(self):
        strcmp = self.module.globals.get("strcmp")
        if strcmp is None:
            strcmp_ty = ir.FunctionType(
                ir.IntType(32),
                [ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer()]
            )
            strcmp = ir.Function(self.module, strcmp_ty, name="strcmp")
        return strcmp

    def _call_strcmp(self, str1, str2):
        """
        Chama strcmp(str1, str2) e retorna i32.
        Retorna: 0 se iguais, <0 se str1 < str2, >0 se str1 > str2
        """
        strcmp = self._get_strcmp()
        return self.builder.call(strcmp, [str1, str2])

    def _get_scanf(self):
        scanf = self.module.globals.get("scanf")
        if scanf is None:
            scanf_ty = ir.FunctionType(
                ir.IntType(32),
                [ir.IntType(8).as_pointer()],
                var_arg=True
            )
            scanf = ir.Function(self.module, scanf_ty, name="scanf")
        return scanf

    def _get_fgets(self):
        fgets = self.module.globals.get("fgets")
        if fgets is None:
            # char* fgets(char* str, int n, FILE* stream)
            fgets_ty = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(8).as_pointer(), ir.IntType(32), ir.IntType(8).as_pointer()]
            )
            fgets = ir.Function(self.module, fgets_ty, name="fgets")
        return fgets

    def _get_stdin(self):
        stdin = self.module.globals.get("stdin")
        if stdin is None:
            # FILE* stdin (ponteiro global)
            stdin = ir.GlobalVariable(self.module, ir.IntType(8).as_pointer(), name="stdin")
            stdin.linkage = 'external'
        return stdin

    def _get_memcpy(self):
        memcpy = self.module.globals.get("memcpy")
        if memcpy is None:
            memcpy_ty = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(8).as_pointer(), ir.IntType(8).as_pointer(), ir.IntType(64)]
            )
            memcpy = ir.Function(self.module, memcpy_ty, name="memcpy")
        return memcpy

    def _builtin_input(self):
        """
        Implementa input() que lê uma linha do stdin e retorna string.
        Usa fgets com buffer de 256 bytes.
        """
        malloc = self._get_malloc()
        fgets = self._get_fgets()
        stdin = self._get_stdin()
        
        # Aloca buffer de 256 bytes
        buffer_size = ir.Constant(ir.IntType(64), 256)
        buffer = self.builder.call(malloc, [buffer_size])
        
        # Chama fgets(buffer, 256, stdin)
        stdin_ptr = self.builder.load(stdin)
        self.builder.call(fgets, [buffer, ir.Constant(ir.IntType(32), 256), stdin_ptr])
        
        # Remove o \n do final se existir
        # Por simplicidade, vamos retornar o buffer direto (pode ter \n no final)
        return buffer

    def _builtin_input_int(self):
        """
        Implementa inputInt() que lê um inteiro do stdin.
        Usa scanf("%d", &var).
        """
        scanf = self._get_scanf()
        
        # Aloca espaço para um int32
        int_ptr = self.builder.alloca(ir.IntType(32))
        
        # Chama scanf("%d", &int_ptr)
        fmt = self._gen_string("%d")
        self.builder.call(scanf, [fmt, int_ptr])
        
        # Retorna o valor lido
        return self.builder.load(int_ptr)

    def _call_setlocale(self):
        """
        Chama setlocale(LC_ALL, ".UTF-8") para configurar UTF-8 no Windows.
        """
        setlocale = self.module.globals.get("setlocale")
        if setlocale is None:
            # char* setlocale(int category, const char* locale)
            setlocale_ty = ir.FunctionType(
                ir.IntType(8).as_pointer(),
                [ir.IntType(32), ir.IntType(8).as_pointer()]
            )
            setlocale = ir.Function(self.module, setlocale_ty, name="setlocale")
        
        # LC_ALL = 0 (valor padrão em C)
        lc_all = ir.Constant(ir.IntType(32), 0)
        
        # String ".UTF-8" para Windows ou "" para usar configuração do sistema
        utf8_locale = self._gen_string(".UTF-8")
        
        # Chama setlocale
        self.builder.call(setlocale, [lc_all, utf8_locale])

    def _concat_strings(self, lhs, rhs):
        """
        Concatena duas strings (i8*) usando strlen, malloc, strcpy e strcat.
        Retorna i8* apontando para a nova string concatenada.
        """
        strlen = self._get_strlen()
        malloc = self._get_malloc()
        strcpy = self._get_strcpy()
        strcat = self._get_strcat()

        # Calcula tamanhos
        len_lhs = self.builder.call(strlen, [lhs])
        len_rhs = self.builder.call(strlen, [rhs])
        total_len = self.builder.add(len_lhs, len_rhs)
        # +1 para null terminator
        alloc_size = self.builder.add(total_len, ir.Constant(ir.IntType(64), 1))

        # Aloca nova string
        result = self.builder.call(malloc, [alloc_size])

        # Copia lhs para result
        self.builder.call(strcpy, [result, lhs])

        # Concatena rhs ao result
        self.builder.call(strcat, [result, rhs])

        return result

    def _gen_logical_and(self, left_expr, right_expr):
        """
        Implementa && com short-circuit: se left é false, não avalia right.
        """
        # Avalia lado esquerdo
        lhs = self._gen_expr(left_expr)
        
        # Converte para bool (i1)
        lhs_bool = self.builder.icmp_signed("!=", lhs, ir.Constant(lhs.type, 0))
        
        # Salva bloco atual
        lhs_block = self.builder.block
        
        # Cria blocos
        then_block = self.func.append_basic_block("and_rhs")
        merge_block = self.func.append_basic_block("and_merge")
        
        # Se lhs é true, avalia rhs; senão pula para merge
        self.builder.cbranch(lhs_bool, then_block, merge_block)
        
        # Bloco THEN: avalia right
        self.builder.position_at_end(then_block)
        rhs = self._gen_expr(right_expr)
        rhs_bool = self.builder.icmp_signed("!=", rhs, ir.Constant(rhs.type, 0))
        then_block = self.builder.block  # Atualiza (pode ter mudado)
        self.builder.branch(merge_block)
        
        # Bloco MERGE: PHI node
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(ir.IntType(1))
        phi.add_incoming(ir.Constant(ir.IntType(1), 0), lhs_block)  # false do lhs
        phi.add_incoming(rhs_bool, then_block)
        
        # Retorna i1 diretamente (booleano)
        return phi

    def _gen_logical_or(self, left_expr, right_expr):
        """
        Implementa || com short-circuit: se left é true, não avalia right.
        """
        # Avalia lado esquerdo
        lhs = self._gen_expr(left_expr)
        
        # Converte para bool (i1)
        lhs_bool = self.builder.icmp_signed("!=", lhs, ir.Constant(lhs.type, 0))
        
        # Salva bloco atual
        lhs_block = self.builder.block
        
        # Cria blocos
        else_block = self.func.append_basic_block("or_rhs")
        merge_block = self.func.append_basic_block("or_merge")
        
        # Se lhs é false, avalia rhs; senão pula para merge com true
        self.builder.cbranch(lhs_bool, merge_block, else_block)
        
        # Bloco ELSE: avalia right
        self.builder.position_at_end(else_block)
        rhs = self._gen_expr(right_expr)
        rhs_bool = self.builder.icmp_signed("!=", rhs, ir.Constant(rhs.type, 0))
        else_block = self.builder.block
        self.builder.branch(merge_block)
        
        # Bloco MERGE: PHI node
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(ir.IntType(1))
        phi.add_incoming(ir.Constant(ir.IntType(1), 1), lhs_block)  # true do lhs
        phi.add_incoming(rhs_bool, else_block)
        
        # Retorna i1 diretamente (booleano)
        return phi

    def _gen_power(self, base, exponent):
        """
        Implementa potência usando llvm.pow.f64 intrinsic.
        Converte inteiros para double, calcula e converte de volta se necessário.
        """
        # Converte operandos para double
        if isinstance(base.type, ir.IntType):
            base_f64 = self.builder.sitofp(base, ir.DoubleType())
        else:
            base_f64 = base
            
        if isinstance(exponent.type, ir.IntType):
            exp_f64 = self.builder.sitofp(exponent, ir.DoubleType())
        else:
            exp_f64 = exponent
        
        # Declara/obtém llvm.pow.f64
        pow_fn = self.module.globals.get("llvm.pow.f64")
        if pow_fn is None:
            pow_ty = ir.FunctionType(ir.DoubleType(), [ir.DoubleType(), ir.DoubleType()])
            pow_fn = ir.Function(self.module, pow_ty, name="llvm.pow.f64")
        
        # Chama pow
        result_f64 = self.builder.call(pow_fn, [base_f64, exp_f64])
        
        # Se ambos operandos originais eram int, converte resultado para int
        if isinstance(base.type, ir.IntType) and isinstance(exponent.type, ir.IntType):
            return self.builder.fptosi(result_f64, ir.IntType(32))
        else:
            return result_f64
