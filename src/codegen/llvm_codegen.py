from llvmlite import ir
from typing import Dict, Optional, Tuple
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, InstrucaoAtribuicao, InstrucaoIf,
    InstrucaoLoopWhile, InstrucaoLoopFor, InstrucaoImpressao,
    InstrucaoRetorno, ExpressaoBinaria, ExpressaoUnaria, Literal,
    Variavel, ChamadaFuncao, ASTNode, CriacaoArray, AcessoArray,
    InstrucaoBreak, InstrucaoContinue
)


class LLVMCodeGenerator:
    def __init__(self):
        self.module = ir.Module(name="module")
        self.builder = None
        self.func = None
        self.symbols: Dict[str, ir.AllocaInstr] = {}  # variáveis locais
        # Pilha de loops: [(continue_block, break_block), ...]
        self.loop_stack: list[Tuple[ir.Block, ir.Block]] = []

    # -------------------------
    # Entrada: gerar código LLVM IR para o programa
    # -------------------------
    def generate(self, program: Programa) -> str:
        # Separa declarações de funções e instruções
        funcoes = [d for d in program.declaracoes if isinstance(d, DeclaracaoFuncao)]
        instrucoes = [d for d in program.declaracoes if not isinstance(d, DeclaracaoFuncao)]
        
        # Verifica se existe uma função main() definida pelo usuário
        user_main = next((f for f in funcoes if f.nome == "main"), None)
        
        # Gera todas as funções primeiro
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
            # Imprime todos os argumentos sequencialmente sem quebra de linha, e ao final imprime \n
            for expr in (node.expressoes or []):
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

            if op == "+":
                # Detecta se é concatenação de strings (i8*) ou adição numérica
                if isinstance(lhs.type, ir.PointerType) and lhs.type.pointee == ir.IntType(8):
                    # Concatenação de strings
                    return self._concat_strings(lhs, rhs)
                else:
                    # Adição aritmética
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
                # Detecta se é comparação float ou inteira
                if isinstance(lhs.type, ir.DoubleType):
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
            elif op == "^":
                # Potência usando llvm.pow intrinsic
                return self._gen_power(lhs, rhs)
            else:
                raise NotImplementedError(f"Operador '{op}' não suportado")

        elif isinstance(expr, ExpressaoUnaria):
            val = self._gen_expr(expr.direita)
            if expr.operador == "-":
                return self.builder.neg(val)
            elif expr.operador == "!":
                # Negação booleana
                return self.builder.icmp_unsigned("==", val, ir.Constant(val.type, 0))
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
                # convert pointers/doubles de forma simples: trunc/bitcast não ideal, mas suficiente para este uso
                size_i64 = size_val if isinstance(size_val.type, ir.IntType) and size_val.type.width == 64 else self.builder.ptrtoint(size_val, ir.IntType(64)) if isinstance(size_val.type, ir.PointerType) else self.builder.fptosi(size_val, ir.IntType(64))

            # multiplica pelo tamanho do elemento (int32 = 4 bytes)
            elem_size = ir.Constant(ir.IntType(64), 4)
            total_bytes = self.builder.mul(size_i64, elem_size)

            malloc = self.module.globals.get("malloc")
            if malloc is None:
                malloc_ty = ir.FunctionType(ir.IntType(8).as_pointer(), [ir.IntType(64)])
                malloc = ir.Function(self.module, malloc_ty, name="malloc")
            raw_ptr = self.builder.call(malloc, [total_bytes])
            # bitcast para i32*
            return self.builder.bitcast(raw_ptr, ir.IntType(32).as_pointer())

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
            # Aloca count * 4 bytes
            malloc = self.module.globals.get("malloc")
            if malloc is None:
                malloc_ty = ir.FunctionType(ir.IntType(8).as_pointer(), [ir.IntType(64)])
                malloc = ir.Function(self.module, malloc_ty, name="malloc")
            total_bytes = ir.Constant(ir.IntType(64), count * 4)
            raw_ptr = self.builder.call(malloc, [total_bytes])
            arr_ptr = self.builder.bitcast(raw_ptr, ir.IntType(32).as_pointer())
            # Inicializa cada elemento
            for i, e in enumerate(elementos):
                val = self._gen_expr(e)
                # Converte float/bool para i32 se necessário
                if isinstance(val.type, ir.DoubleType):
                    val = self.builder.fptosi(val, ir.IntType(32))
                elif isinstance(val.type, ir.IntType) and val.type.width != 32:
                    # booleans i1
                    val = self.builder.zext(val, ir.IntType(32)) if val.type.width < 32 else self.builder.trunc(val, ir.IntType(32))
                elif isinstance(val.type, ir.PointerType):
                    # Não suportamos strings em literal de array aqui
                    raise TypeError("Literal de array suporta apenas inteiros por enquanto")
                idx = ir.Constant(ir.IntType(32), i)
                elem_ptr = self.builder.gep(arr_ptr, [idx])
                self.builder.store(val, elem_ptr)
            return arr_ptr

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
