from llvmlite import ir
from typing import Dict, Optional, Tuple
from src.parser.ast.ast_base import (
    Programa, DeclaracaoFuncao, DeclaracaoMetodo, InstrucaoAtribuicao, InstrucaoIf,
    InstrucaoLoopWhile, InstrucaoLoopFor, InstrucaoImpressao,
    InstrucaoRetorno, ExpressaoBinaria, ExpressaoUnaria, Literal,
    Variavel, ChamadaFuncao, ASTNode, CriacaoArray, AcessoArray,
    InstrucaoBreak, InstrucaoContinue, LiteralArray, InstrucaoLoopInfinito,
    DeclaracaoClasse, CriacaoClasse, AcessoCampo, InstrucaoLoopForEach, LiteralRange, CriacaoArray2D, LiteralTuple, DeclaracaoEnum, CriacaoMapa
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
        # Metadados para mapas: nome -> tipos
        self.maps: Dict[str, Dict[str, ir.Type]] = {}
        # Generics: rastreia declarações genéricas e instanciações
        self.generic_functions: Dict[str, DeclaracaoFuncao] = {}  # nome -> declaração
        self.generic_classes: Dict[str, DeclaracaoClasse] = {}  # nome -> declaração
        self.instantiated_functions: Dict[Tuple[str, Tuple[str, ...]], str] = {}  # (nome, tipos) -> nome_mangled
        self.instantiated_classes: Dict[Tuple[str, Tuple[str, ...]], str] = {}  # (nome, tipos) -> nome_mangled

    # -------------------------
    # Entrada: gerar código LLVM IR para o programa
    # -------------------------
    def generate(self, program: Programa) -> str:
        # Separa declarações de funções, classes e instruções
        classes = [d for d in program.declaracoes if isinstance(d, DeclaracaoClasse)]
        enums = [d for d in program.declaracoes if isinstance(d, DeclaracaoEnum)]
        funcoes = [d for d in program.declaracoes if isinstance(d, DeclaracaoFuncao)]
        metodos: list[tuple[str, DeclaracaoMetodo]] = []
        instrucoes = [d for d in program.declaracoes if not isinstance(d, (DeclaracaoFuncao, DeclaracaoClasse))]
        
        # Separa classes/funções genéricas de não-genéricas
        for class_decl in classes:
            if getattr(class_decl, 'type_params', None):
                # Classe genérica: apenas registra para instanciação posterior
                self.generic_classes[class_decl.nome] = class_decl
            else:
                # Classe normal: registra imediatamente
                self._register_class(class_decl)
            for m in getattr(class_decl, 'metodos', []) or []:
                metodos.append((class_decl.nome, m))
        
        for enum_decl in enums:
            # Registra enums para uso como constantes (i32)
            self._register_enum(enum_decl)
        
        # Separa funções genéricas
        for func_decl in funcoes:
            if getattr(func_decl, 'type_params', None):
                # Função genérica: apenas registra para instanciação posterior
                self.generic_functions[func_decl.nome] = func_decl
            else:
                # Função normal: gera código imediatamente
                self._gen_function(func_decl)
        
        # Verifica se existe uma função main() definida pelo usuário
        user_main = next((f for f in funcoes if f.nome == "main"), None)
        
        # Gera métodos primeiro (declaração disponível para funções que os chamam)
        for class_name, metodo in metodos:
            # Pula métodos de classes genéricas (serão gerados ao instanciar)
            if class_name not in self.generic_classes:
                self._gen_method(class_name, metodo)
        
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
                    
                    # Promove/coerção: se um é double e outro int, converte int para double
                    if isinstance(current_val.type, ir.DoubleType) and isinstance(rhs_val.type, ir.IntType):
                        rhs_val = self.builder.sitofp(rhs_val, ir.DoubleType())
                    elif isinstance(rhs_val.type, ir.DoubleType) and isinstance(current_val.type, ir.IntType):
                        current_val = self.builder.sitofp(current_val, ir.DoubleType())

                    # Realiza a operação respeitando tipo (int vs double)
                    if node.operador == '+=':
                        new_val = self.builder.fadd(current_val, rhs_val) if isinstance(current_val.type, ir.DoubleType) else self.builder.add(current_val, rhs_val)
                    elif node.operador == '-=':
                        new_val = self.builder.fsub(current_val, rhs_val) if isinstance(current_val.type, ir.DoubleType) else self.builder.sub(current_val, rhs_val)
                    elif node.operador == '*=':
                        new_val = self.builder.fmul(current_val, rhs_val) if isinstance(current_val.type, ir.DoubleType) else self.builder.mul(current_val, rhs_val)
                    elif node.operador == '/=':
                        new_val = self.builder.fdiv(current_val, rhs_val) if isinstance(current_val.type, ir.DoubleType) else self.builder.sdiv(current_val, rhs_val)
                    
                    self.builder.store(new_val, self.symbols[name])
                else:
                    # Atribuição simples: =
                    val = self._gen_expr(node.valor)
                    if name not in self.symbols:
                        alloca = self._entry_alloca(val.type, name=name)
                        self.symbols[name] = alloca
                    else:
                        # Se o valor é null (i8*) e a variável é de outro tipo de ponteiro, faz cast
                        target_type = self.symbols[name].type.pointee
                        if isinstance(val.type, ir.PointerType) and isinstance(target_type, ir.PointerType):
                            if val.type != target_type:
                                val = self.builder.bitcast(val, target_type)
                    self.builder.store(val, self.symbols[name])
                    # Se criando mapa, registra metadados
                    if isinstance(node.valor, CriacaoMapa):
                        key_ty = self._type_from_name(node.valor.tipo_chave)
                        self.maps[name] = {
                            'key_ty': key_ty,
                            'val_ty': self._type_from_name(node.valor.tipo_valor)
                        }
            # Atribuição para elemento de array: alvo[indice] = valor
            elif isinstance(node.alvo, AcessoArray):
                # Set em array ou mapa
                if isinstance(node.alvo.alvo, Variavel) and node.alvo.alvo.nome in self.maps:
                    map_ptr = self._gen_expr(node.alvo.alvo)
                    key_val = self._gen_expr(node.alvo.indice)
                    val = self._gen_expr(node.valor)
                    def gep_field(idx):
                        return self.builder.gep(map_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
                    kptr = self.builder.load(gep_field(0))
                    vptr = self.builder.load(gep_field(1))
                    cap = self.builder.load(gep_field(2))
                    size_ptr = gep_field(3)
                    size = self.builder.load(size_ptr)
                    # loop de busca
                    i_alloc = self._entry_alloca(ir.IntType(32), name="_map_i")
                    self.builder.store(ir.Constant(ir.IntType(32), 0), i_alloc)
                    start_b = self.func.append_basic_block("map_set_start")
                    body_b = self.func.append_basic_block("map_set_body")
                    step_b = self.func.append_basic_block("map_set_step")
                    end_b = self.func.append_basic_block("map_set_end")
                    found_b = self.func.append_basic_block("map_set_found")
                    insert_b = self.func.append_basic_block("map_set_insert")
                    self.builder.branch(start_b)
                    self.builder.position_at_end(start_b)
                    i_val = self.builder.load(i_alloc)
                    cond = self.builder.icmp_signed("<", i_val, size)
                    self.builder.cbranch(cond, body_b, insert_b)
                    self.builder.position_at_end(body_b)
                    k_elemptr = self.builder.gep(kptr, [i_val])
                    k_elem = self.builder.load(k_elemptr)
                    # Comparação de chave por tipo
                    if isinstance(k_elem.type, ir.IntType):
                        # normaliza key_val para mesma largura
                        if isinstance(key_val.type, ir.IntType) and key_val.type.width != k_elem.type.width:
                            key_val = self.builder.zext(key_val, k_elem.type) if key_val.type.width < k_elem.type.width else self.builder.trunc(key_val, k_elem.type)
                        elif isinstance(key_val.type, ir.DoubleType):
                            key_val = self.builder.fptosi(key_val, k_elem.type)
                        eq = self.builder.icmp_signed("==", k_elem, key_val)
                    elif isinstance(k_elem.type, ir.DoubleType):
                        if isinstance(key_val.type, ir.IntType):
                            key_val = self.builder.sitofp(key_val, ir.DoubleType())
                        eq = self.builder.fcmp_ordered("==", k_elem, key_val)
                    elif isinstance(k_elem.type, ir.PointerType) and isinstance(k_elem.type.pointee, ir.LiteralStructType):
                        # Chave é classe: tenta chamar método equals(self, other): bool
                        class_name = None
                        for name, (stype, _fmap) in self.classes.items():
                            if stype == k_elem.type.pointee:
                                class_name = name
                                break
                        if class_name is not None:
                            equals_fn = self.module.globals.get(f"{class_name}_equals")
                            if equals_fn is not None:
                                # Garante tipos de ponteiro compatíveis
                                lhs_ptr = k_elem
                                rhs_ptr = key_val
                                if lhs_ptr.type != equals_fn.function_type.args[0]:
                                    # bitcast self
                                    lhs_ptr = self.builder.bitcast(lhs_ptr, equals_fn.function_type.args[0])
                                if rhs_ptr.type != equals_fn.function_type.args[1]:
                                    rhs_ptr = self.builder.bitcast(rhs_ptr, equals_fn.function_type.args[1])
                                eq_res = self.builder.call(equals_fn, [lhs_ptr, rhs_ptr])
                                # equals retorna i1; usa diretamente
                                eq = eq_res
                            else:
                                # Fallback: compara ponteiros
                                eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                        else:
                            eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                    elif isinstance(k_elem.type, ir.PointerType) and isinstance(k_elem.type.pointee, ir.IntType) and k_elem.type.pointee.width == 8:
                        # Strings: usa strcmp
                        strcmp_res = self._call_strcmp(k_elem, key_val)
                        eq = self.builder.icmp_signed("==", strcmp_res, ir.Constant(ir.IntType(32), 0))
                    else:
                        # Fallback: compara ponteiro
                        eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                    self.builder.cbranch(eq, found_b, step_b)
                    self.builder.position_at_end(step_b)
                    i_next = self.builder.add(i_val, ir.Constant(ir.IntType(32), 1))
                    self.builder.store(i_next, i_alloc)
                    self.builder.branch(start_b)
                    self.builder.position_at_end(found_b)
                    v_elemptr = self.builder.gep(vptr, [i_val])
                    # ajuste tipo
                    vty = v_elemptr.type.pointee
                    if isinstance(vty, ir.DoubleType) and isinstance(val.type, ir.IntType):
                        val = self.builder.sitofp(val, ir.DoubleType())
                    elif isinstance(vty, ir.IntType) and isinstance(val.type, ir.DoubleType):
                        val = self.builder.fptosi(val, vty)
                    elif isinstance(vty, ir.IntType) and isinstance(val.type, ir.IntType) and vty.width != val.type.width:
                        val = self.builder.zext(val, vty) if val.type.width < vty.width else self.builder.trunc(val, vty)
                    elif isinstance(vty, ir.PointerType) and isinstance(val.type, ir.PointerType) and vty != val.type:
                        val = self.builder.bitcast(val, vty)
                    self.builder.store(val, v_elemptr)
                    self.builder.branch(end_b)
                    self.builder.position_at_end(insert_b)
                    can_ins = self.builder.icmp_signed("<", size, cap)
                    after_ins_b = self.func.append_basic_block("map_set_afterins")
                    self.builder.cbranch(can_ins, after_ins_b, end_b)
                    self.builder.position_at_end(after_ins_b)
                    k_elemptr2 = self.builder.gep(kptr, [size])
                    v_elemptr2 = self.builder.gep(vptr, [size])
                    # Armazena a chave com normalização de tipo
                    kty = k_elemptr2.type.pointee
                    key_store = key_val
                    if isinstance(kty, ir.IntType):
                        if isinstance(key_store.type, ir.IntType) and key_store.type.width != kty.width:
                            key_store = self.builder.zext(key_store, kty) if key_store.type.width < kty.width else self.builder.trunc(key_store, kty)
                        elif isinstance(key_store.type, ir.DoubleType):
                            key_store = self.builder.fptosi(key_store, kty)
                    elif isinstance(kty, ir.DoubleType):
                        if isinstance(key_store.type, ir.IntType):
                            key_store = self.builder.sitofp(key_store, ir.DoubleType())
                    elif isinstance(kty, ir.PointerType) and isinstance(kty.pointee, ir.IntType) and kty.pointee.width == 8:
                        if not (isinstance(key_store.type, ir.PointerType) and isinstance(key_store.type.pointee, ir.IntType) and key_store.type.pointee.width == 8):
                            key_store = self.builder.bitcast(key_store, ir.IntType(8).as_pointer())
                    self.builder.store(key_store, k_elemptr2)
                    # ajustar tipo para store
                    vty2 = v_elemptr2.type.pointee
                    val2 = val
                    if isinstance(vty2, ir.DoubleType) and isinstance(val2.type, ir.IntType):
                        val2 = self.builder.sitofp(val2, ir.DoubleType())
                    elif isinstance(vty2, ir.IntType) and isinstance(val2.type, ir.DoubleType):
                        val2 = self.builder.fptosi(val2, vty2)
                    elif isinstance(vty2, ir.IntType) and isinstance(val2.type, ir.IntType) and vty2.width != val2.type.width:
                        val2 = self.builder.zext(val2, vty2) if val2.type.width < vty2.width else self.builder.trunc(val2, vty2)
                    elif isinstance(vty2, ir.PointerType) and isinstance(val2.type, ir.PointerType) and vty2 != val2.type:
                        val2 = self.builder.bitcast(val2, vty2)
                    self.builder.store(val2, v_elemptr2)
                    size_inc = self.builder.add(size, ir.Constant(ir.IntType(32), 1))
                    self.builder.store(size_inc, size_ptr)
                    self.builder.branch(end_b)
                    self.builder.position_at_end(end_b)
                else:
                    val = self._gen_expr(node.valor)
                    base_ptr = self._gen_expr(node.alvo.alvo)  # elem*
                    index_val = self._gen_expr(node.alvo.indice)
                    if not isinstance(index_val.type, ir.IntType):
                        index_val = self.builder.ptrtoint(index_val, ir.IntType(32)) if isinstance(index_val.type, ir.PointerType) else self.builder.trunc(index_val, ir.IntType(32))
                    elem_ptr = self.builder.gep(base_ptr, [index_val])
                    elem_ty = elem_ptr.type.pointee
                    if isinstance(elem_ty, ir.IntType) and elem_ty.width == 1:
                        if isinstance(val.type, ir.IntType) and val.type.width != 1:
                            val = self.builder.icmp_signed("!=", val, ir.Constant(val.type, 0))
                        elif isinstance(val.type, ir.DoubleType):
                            val = self.builder.fcmp_ordered("!=", val, ir.Constant(val.type, 0.0))
                    if isinstance(elem_ty, ir.DoubleType) and isinstance(val.type, ir.IntType):
                        val = self.builder.sitofp(val, ir.DoubleType())
                    elif isinstance(elem_ty, ir.IntType) and isinstance(val.type, ir.DoubleType):
                        val = self.builder.fptosi(val, elem_ty)
                    elif isinstance(elem_ty, ir.IntType) and isinstance(val.type, ir.IntType) and elem_ty.width != val.type.width:
                        val = self.builder.zext(val, elem_ty) if val.type.width < elem_ty.width else self.builder.trunc(val, elem_ty)
                    elif isinstance(elem_ty, ir.PointerType) and isinstance(val.type, ir.PointerType) and elem_ty != val.type:
                        val = self.builder.bitcast(val, elem_ty)
                    self.builder.store(val, elem_ptr)
            # Atribuição para campo de classe: objeto.campo = valor ou composto
            elif isinstance(node.alvo, AcessoCampo):
                campo = node.alvo
                obj_ptr = self._gen_expr(campo.alvo)  # ponteiro para struct
                # Descobre classe
                if not (isinstance(obj_ptr.type, ir.PointerType) and isinstance(obj_ptr.type.pointee, ir.LiteralStructType)):
                    raise TypeError("Acesso a campo em objeto não-struct")
                class_name = None
                for name, (stype, fmap) in self.classes.items():
                    if stype == obj_ptr.type.pointee:
                        class_name = name
                        field_map = fmap
                        break
                if class_name is None:
                    raise NameError("Classe do objeto não encontrada para atribuição de campo")
                if campo.campo not in field_map:
                    raise AttributeError(f"Campo '{campo.campo}' inexistente em classe '{class_name}'")
                field_idx = field_map[campo.campo]
                field_ptr = self.builder.gep(obj_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), field_idx)])
                if node.operador in ('+=','-=','*=','/='):
                    current_val = self.builder.load(field_ptr)
                    rhs_val = self._gen_expr(node.valor)
                    # Converte tipos simples se necessário (int/double)
                    if isinstance(current_val.type, ir.DoubleType) and isinstance(rhs_val.type, ir.IntType):
                        rhs_val = self.builder.sitofp(rhs_val, ir.DoubleType())
                    elif isinstance(rhs_val.type, ir.DoubleType) and isinstance(current_val.type, ir.IntType):
                        current_val = self.builder.sitofp(current_val, ir.DoubleType())
                    if node.operador == '+=':
                        new_val = self.builder.add(current_val, rhs_val) if not isinstance(current_val.type, ir.DoubleType) else self.builder.fadd(current_val, rhs_val)
                    elif node.operador == '-=':
                        new_val = self.builder.sub(current_val, rhs_val) if not isinstance(current_val.type, ir.DoubleType) else self.builder.fsub(current_val, rhs_val)
                    elif node.operador == '*=':
                        new_val = self.builder.mul(current_val, rhs_val) if not isinstance(current_val.type, ir.DoubleType) else self.builder.fmul(current_val, rhs_val)
                    elif node.operador == '/=':
                        new_val = self.builder.sdiv(current_val, rhs_val) if not isinstance(current_val.type, ir.DoubleType) else self.builder.fdiv(current_val, rhs_val)
                    self.builder.store(new_val, field_ptr)
                else:
                    val = self._gen_expr(node.valor)
                    # Ajusta tipo se necessário
                    current_ty = field_ptr.type.pointee
                    if isinstance(current_ty, ir.DoubleType) and isinstance(val.type, ir.IntType):
                        val = self.builder.sitofp(val, ir.DoubleType())
                    elif isinstance(current_ty, ir.IntType) and current_ty.width == 32 and isinstance(val.type, ir.IntType) and val.type.width != 32:
                        # Normaliza para i32
                        if val.type.width < 32:
                            val = self.builder.zext(val, ir.IntType(32))
                        else:
                            val = self.builder.trunc(val, ir.IntType(32))
                    self.builder.store(val, field_ptr)
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
                elif isinstance(val.type, ir.IntType) and val.type.width == 8:
                    # imprime byte como caractere
                    fmt = self._gen_string("%c")
                    promoted = self.builder.zext(val, ir.IntType(32))
                    self.builder.call(printf, [fmt, promoted])
                elif isinstance(val.type, ir.IntType) and val.type.width == 1:
                    fmt = self._gen_string("%d")
                    # promove para i32 para variádico
                    promoted = self.builder.zext(val, ir.IntType(32))
                    self.builder.call(printf, [fmt, promoted])
                else:
                    fmt = self._gen_string("%d")
                    # Se inteiro não-i32, promove/trunca para i32
                    if isinstance(val.type, ir.IntType) and val.type.width != 32:
                        if val.type.width < 32:
                            val = self.builder.zext(val, ir.IntType(32))
                        else:
                            val = self.builder.trunc(val, ir.IntType(32))
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
        elif isinstance(node, InstrucaoLoopForEach):
            self._gen_foreach(node)

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
            # Importante: bool antes de int (bool é subclass de int em Python)
            if isinstance(expr.valor, bool):
                # true -> 1, false -> 0 (i1)
                return ir.Constant(ir.IntType(1), int(expr.valor))
            if isinstance(expr.valor, int):
                return ir.Constant(ir.IntType(32), expr.valor)
            elif isinstance(expr.valor, float):
                return ir.Constant(ir.DoubleType(), expr.valor)
            elif isinstance(expr.valor, str):
                # string ou char
                return self._gen_string(expr.valor)
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
            
            # Verifica se é uma função genérica sendo chamada com argumentos de tipo
            type_args = getattr(expr, 'type_args', None)
            if type_args and isinstance(fn_name, str):
                # Instancia a função genérica para esses tipos
                mangled_name = self._instantiate_generic_function(fn_name, tuple(type_args))
                # Chama a versão concreta
                func = self.module.globals.get(mangled_name)
                if func is None:
                    raise NameError(f"Função genérica instanciada '{mangled_name}' não encontrada")
                args = [self._gen_expr(a) for a in (expr.argumentos or [])]
                return self.builder.call(func, args)
            
            # Verifica se é uma criação de classe
            if isinstance(fn_name, str) and fn_name in self.classes:
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
            
            # Suporte a chamada de método: alvo.metodo(args)
            if isinstance(expr.nome, AcessoCampo):
                alvo_ptr = self._gen_expr(expr.nome.alvo)
                if isinstance(alvo_ptr.type, ir.PointerType) and isinstance(alvo_ptr.type.pointee, ir.LiteralStructType):
                    class_name = None
                    for name, (stype, _field_map) in self.classes.items():
                        if stype == alvo_ptr.type.pointee:
                            class_name = name
                            break
                    if class_name is None:
                        raise NameError("Classe do alvo não identificada para chamada de método")
                    mangled = f"{class_name}_{expr.nome.campo}"
                    func = self.module.globals.get(mangled)
                    if func is None:
                        raise NameError(f"Método '{expr.nome.campo}' de '{class_name}' não declarado")
                    call_args = [alvo_ptr] + [self._gen_expr(a) for a in (expr.argumentos or [])]
                    return self.builder.call(func, call_args)

            func = self.module.globals.get(fn_name)
            if func is None:
                raise NameError(f"Função '{fn_name}' não declarada")
            args = [self._gen_expr(a) for a in (expr.argumentos or [])]
            return self.builder.call(func, args)

        elif isinstance(expr, CriacaoArray2D):
            # new T[m][n]: array de pointers para T[]
            m_val = self._gen_expr(expr.linhas)
            n_val = self._gen_expr(expr.colunas)
            # outer: elementos são ponteiros para inner elem
            inner_elem_ty = self._type_from_name(expr.tipo)
            if isinstance(inner_elem_ty, ir.IntType) and inner_elem_ty.width == 1:
                pass
            outer_elem_ty = inner_elem_ty.as_pointer()
            # Aloca outer como array de ponteiros
            # Reimplementa com elem ponteiro e usa m (expr.linhas) como tamanho
            size_val = m_val
            # i64
            if isinstance(size_val.type, ir.IntType) and size_val.type.width < 64:
                size_i64 = self.builder.sext(size_val, ir.IntType(64))
            elif isinstance(size_val.type, ir.IntType) and size_val.type.width > 64:
                size_i64 = self.builder.trunc(size_val, ir.IntType(64))
            else:
                size_i64 = size_val if isinstance(size_val.type, ir.IntType) and size_val.type.width == 64 else self.builder.fptosi(size_val, ir.IntType(64))
            # ponteiro tem 8 bytes
            elem_size = ir.Constant(ir.IntType(64), 8)
            data_bytes = self.builder.mul(size_i64, elem_size)
            header_bytes = ir.Constant(ir.IntType(64), 8)
            total_bytes = self.builder.add(header_bytes, data_bytes)
            malloc = self._get_malloc()
            raw_ptr = self.builder.call(malloc, [total_bytes])
            len_ptr = self.builder.bitcast(raw_ptr, ir.IntType(64).as_pointer())
            self.builder.store(size_i64, len_ptr)
            data_i8 = self.builder.gep(raw_ptr, [ir.Constant(ir.IntType(32), 8)])
            outer_ptr = self.builder.bitcast(data_i8, outer_elem_ty.as_pointer())  # (T*)*

            # Loop i=0..m-1: outer[i] = new T[n]
            i_alloc = self._entry_alloca(ir.IntType(32), name="_i_rows")
            self.builder.store(ir.Constant(ir.IntType(32), 0), i_alloc)
            start_b = self.func.append_basic_block("rows_start")
            body_b = self.func.append_basic_block("rows_body")
            step_b = self.func.append_basic_block("rows_step")
            end_b = self.func.append_basic_block("rows_end")
            self.builder.branch(start_b)
            self.builder.position_at_end(start_b)
            i_val = self.builder.load(i_alloc)
            m32 = size_val if (isinstance(size_val.type, ir.IntType) and size_val.type.width == 32) else self.builder.trunc(size_i64, ir.IntType(32))
            cond = self.builder.icmp_signed("<", i_val, m32)
            self.builder.cbranch(cond, body_b, end_b)

            self.builder.position_at_end(body_b)
            # cria inner array new T[n]
            inner_arr = CriacaoArray(expr.tipo, expr.colunas)
            inner_ptr = self._gen_expr(inner_arr)
            elem_ptr = self.builder.gep(outer_ptr, [i_val])
            # store pointer
            self.builder.store(inner_ptr, elem_ptr)
            self.builder.branch(step_b)

            self.builder.position_at_end(step_b)
            i_next = self.builder.add(i_val, ir.Constant(ir.IntType(32), 1))
            self.builder.store(i_next, i_alloc)
            self.builder.branch(start_b)

            self.builder.position_at_end(end_b)
            return outer_ptr

        elif isinstance(expr, CriacaoArray):
            # Cria array tipado com header i64 (length) e dados consecutivos
            size_val = self._gen_expr(expr.tamanho)
            # garante i64 para malloc size
            if isinstance(size_val.type, ir.IntType) and size_val.type.width < 64:
                size_i64 = self.builder.sext(size_val, ir.IntType(64))
            elif isinstance(size_val.type, ir.IntType) and size_val.type.width > 64:
                size_i64 = self.builder.trunc(size_val, ir.IntType(64))
            else:
                size_i64 = size_val if isinstance(size_val.type, ir.IntType) and size_val.type.width == 64 else self.builder.ptrtoint(size_val, ir.IntType(64)) if isinstance(size_val.type, ir.PointerType) else self.builder.fptosi(size_val, ir.IntType(64))

            elem_ty = self._type_from_name(expr.tipo)
            # tamanho do elemento
            if isinstance(elem_ty, ir.IntType):
                elem_bytes = elem_ty.width // 8 if elem_ty.width >= 8 else 1
            elif isinstance(elem_ty, ir.DoubleType):
                elem_bytes = 8
            elif isinstance(elem_ty, ir.FloatType):
                elem_bytes = 4
            elif isinstance(elem_ty, ir.PointerType):
                elem_bytes = 8
            else:
                elem_bytes = 8
            elem_size = ir.Constant(ir.IntType(64), elem_bytes)
            data_bytes = self.builder.mul(size_i64, elem_size)
            header_bytes = ir.Constant(ir.IntType(64), 8)
            total_bytes = self.builder.add(header_bytes, data_bytes)

            malloc = self._get_malloc()
            raw_ptr = self.builder.call(malloc, [total_bytes])  # i8*

            # Salva length no header (i64)
            len_ptr = self.builder.bitcast(raw_ptr, ir.IntType(64).as_pointer())
            self.builder.store(size_i64, len_ptr)

            # Data pointer é raw_ptr + 8, como elem_ty*
            data_i8 = self.builder.gep(raw_ptr, [ir.Constant(ir.IntType(32), 8)])
            data_ptr = self.builder.bitcast(data_i8, elem_ty.as_pointer())
            return data_ptr

        elif isinstance(expr, CriacaoMapa):
            # struct Map { K* keys; V* values; i32 capacity; i32 size; }
            # Usa mapeamento padrão de tipos para chave/valor
            key_elem_ty = self._type_from_name(expr.tipo_chave)
            val_ty = self._type_from_name(expr.tipo_valor)

            # Ponteiro para o array de chaves: K*
            keys_arr_ptr_ty = key_elem_ty.as_pointer()

            map_struct = ir.LiteralStructType([keys_arr_ptr_ty, val_ty.as_pointer(), ir.IntType(32), ir.IntType(32)])
            malloc = self._get_malloc()
            raw = self.builder.call(malloc, [ir.Constant(ir.IntType(64), 32)])
            map_ptr = self.builder.bitcast(raw, map_struct.as_pointer())

            # capacidade
            cap32 = self._gen_expr(expr.capacidade)
            if not (isinstance(cap32.type, ir.IntType) and cap32.type.width == 32):
                cap32 = self.builder.trunc(cap32, ir.IntType(32)) if isinstance(cap32.type, ir.IntType) else self.builder.fptosi(cap32, ir.IntType(32))

            # aloca arrays keys e values: calcula bytes por elemento
            if isinstance(key_elem_ty, ir.IntType):
                k_elem_bytes = ir.Constant(ir.IntType(64), max(1, key_elem_ty.width // 8))
            elif isinstance(key_elem_ty, ir.DoubleType):
                k_elem_bytes = ir.Constant(ir.IntType(64), 8)
            elif isinstance(key_elem_ty, ir.FloatType):
                k_elem_bytes = ir.Constant(ir.IntType(64), 4)
            elif isinstance(key_elem_ty, ir.PointerType):
                k_elem_bytes = ir.Constant(ir.IntType(64), 8)
            else:
                k_elem_bytes = ir.Constant(ir.IntType(64), 8)
            key_bytes = self.builder.mul(self.builder.sext(cap32, ir.IntType(64)), k_elem_bytes)
            kraw = self.builder.call(malloc, [key_bytes])
            kptr = self.builder.bitcast(kraw, key_elem_ty.as_pointer())

            # valores
            if isinstance(val_ty, ir.IntType):
                v_elem_bytes = ir.Constant(ir.IntType(64), max(1, val_ty.width // 8))
            elif isinstance(val_ty, ir.DoubleType):
                v_elem_bytes = ir.Constant(ir.IntType(64), 8)
            elif isinstance(val_ty, ir.FloatType):
                v_elem_bytes = ir.Constant(ir.IntType(64), 4)
            elif isinstance(val_ty, ir.PointerType):
                v_elem_bytes = ir.Constant(ir.IntType(64), 8)
            else:
                v_elem_bytes = ir.Constant(ir.IntType(64), 8)
            v_bytes = self.builder.mul(self.builder.sext(cap32, ir.IntType(64)), v_elem_bytes)
            vraw = self.builder.call(malloc, [v_bytes])
            vptr = self.builder.bitcast(vraw, val_ty.as_pointer())

            # campos
            def gep_field(idx):
                return self.builder.gep(map_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
            self.builder.store(kptr, gep_field(0))
            self.builder.store(vptr, gep_field(1))
            self.builder.store(cap32, gep_field(2))
            self.builder.store(ir.Constant(ir.IntType(32), 0), gep_field(3))
            return map_ptr

        elif isinstance(expr, AcessoArray):
            # Mapa: m[key]
            if isinstance(expr.alvo, Variavel) and expr.alvo.nome in self.maps:
                map_ptr = self._gen_expr(expr.alvo)
                key_val = self._gen_expr(expr.indice)
                # Normaliza chave conforme tipo do mapa
                # Busca tipo da chave pelo metadado
                meta = None
                for var_name, types in self.maps.items():
                    if var_name == expr.alvo.nome:
                        meta = types
                        break
                if meta is not None:
                    kty = meta['key_ty']
                    if isinstance(kty, ir.IntType):
                        if isinstance(key_val.type, ir.IntType) and key_val.type.width != kty.width:
                            key_val = self.builder.zext(key_val, kty) if key_val.type.width < kty.width else self.builder.trunc(key_val, kty)
                        elif isinstance(key_val.type, ir.DoubleType):
                            key_val = self.builder.fptosi(key_val, kty)
                    elif isinstance(kty, ir.DoubleType):
                        if isinstance(key_val.type, ir.IntType):
                            key_val = self.builder.sitofp(key_val, ir.DoubleType())
                    else:
                        # espera i8*; se for string literal já é i8*
                        if not (isinstance(key_val.type, ir.PointerType) and isinstance(key_val.type.pointee, ir.IntType) and key_val.type.pointee.width == 8):
                            key_val = self.builder.bitcast(key_val, ir.IntType(8).as_pointer())
                def gep_field(idx):
                    return self.builder.gep(map_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
                kptr = self.builder.load(gep_field(0))
                vptr = self.builder.load(gep_field(1))
                size = self.builder.load(gep_field(3))
                i_alloc = self._entry_alloca(ir.IntType(32), name="_map_i_get")
                self.builder.store(ir.Constant(ir.IntType(32), 0), i_alloc)
                start_b = self.func.append_basic_block("map_get_start")
                body_b = self.func.append_basic_block("map_get_body")
                step_b = self.func.append_basic_block("map_get_step")
                end_b = self.func.append_basic_block("map_get_end")
                found_b = self.func.append_basic_block("map_get_found")
                self.builder.branch(start_b)
                self.builder.position_at_end(start_b)
                i_val = self.builder.load(i_alloc)
                cond = self.builder.icmp_signed("<", i_val, size)
                self.builder.cbranch(cond, body_b, end_b)
                self.builder.position_at_end(body_b)
                k_elemptr = self.builder.gep(kptr, [i_val])
                k_elem = self.builder.load(k_elemptr)
                # Comparação por tipo
                if isinstance(k_elem.type, ir.IntType):
                    eq = self.builder.icmp_signed("==", k_elem, key_val)
                elif isinstance(k_elem.type, ir.DoubleType):
                    eq = self.builder.fcmp_ordered("==", k_elem, key_val)
                elif isinstance(k_elem.type, ir.PointerType) and isinstance(k_elem.type.pointee, ir.LiteralStructType):
                    # Chave é classe: tenta método equals
                    class_name = None
                    for name, (stype, _fmap) in self.classes.items():
                        if stype == k_elem.type.pointee:
                            class_name = name
                            break
                    if class_name is not None:
                        equals_fn = self.module.globals.get(f"{class_name}_equals")
                        if equals_fn is not None:
                            lhs_ptr = k_elem
                            rhs_ptr = key_val
                            if lhs_ptr.type != equals_fn.function_type.args[0]:
                                lhs_ptr = self.builder.bitcast(lhs_ptr, equals_fn.function_type.args[0])
                            if rhs_ptr.type != equals_fn.function_type.args[1]:
                                rhs_ptr = self.builder.bitcast(rhs_ptr, equals_fn.function_type.args[1])
                            eq = self.builder.call(equals_fn, [lhs_ptr, rhs_ptr])
                        else:
                            eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                    else:
                        eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                elif isinstance(k_elem.type, ir.PointerType) and isinstance(k_elem.type.pointee, ir.IntType) and k_elem.type.pointee.width == 8:
                    strcmp_res = self._call_strcmp(k_elem, key_val)
                    eq = self.builder.icmp_signed("==", strcmp_res, ir.Constant(ir.IntType(32), 0))
                else:
                    eq = self.builder.icmp_unsigned("==", k_elem, key_val)
                self.builder.cbranch(eq, found_b, step_b)
                self.builder.position_at_end(step_b)
                i_next = self.builder.add(i_val, ir.Constant(ir.IntType(32), 1))
                self.builder.store(i_next, i_alloc)
                self.builder.branch(start_b)
                self.builder.position_at_end(found_b)
                v_elemptr = self.builder.gep(vptr, [i_val])
                val = self.builder.load(v_elemptr)
                self.builder.branch(end_b)
                self.builder.position_at_end(end_b)
                phi = self.builder.phi(val.type)
                default_val = ir.Constant(val.type, 0) if isinstance(val.type, ir.IntType) or isinstance(val.type, ir.DoubleType) else ir.Constant(val.type, None) if isinstance(val.type, ir.PointerType) else ir.Constant(val.type, 0)
                phi.add_incoming(default_val, start_b)
                phi.add_incoming(val, found_b)
                return phi

            base_ptr = self._gen_expr(expr.alvo)  # elem*
            # Acesso a tupla por índice: se alvo é struct literal, usa GEP no struct
            if isinstance(base_ptr.type, ir.PointerType) and isinstance(base_ptr.type.pointee, ir.LiteralStructType):
                index_val = self._gen_expr(expr.indice)
                if not isinstance(index_val.type, ir.IntType):
                    index_val = self.builder.trunc(index_val, ir.IntType(32)) if isinstance(index_val.type, ir.IntType) else self.builder.fptosi(index_val, ir.IntType(32))
                field_ptr = self.builder.gep(base_ptr, [ir.Constant(ir.IntType(32), 0), index_val])
                return self.builder.load(field_ptr)
            # Slicing: indice é range
            if isinstance(expr.indice, LiteralRange) or (isinstance(expr.indice, ExpressaoBinaria) and expr.indice.operador == ".."):
                # Calcula start e end em i32
                if isinstance(expr.indice, LiteralRange):
                    start_val = self._gen_expr(expr.indice.inicio)
                    end_val = self._gen_expr(expr.indice.fim)
                else:
                    start_val = self._gen_expr(expr.indice.esquerda)
                    end_val = self._gen_expr(expr.indice.direita)
                # Normaliza para i32
                if not (isinstance(start_val.type, ir.IntType) and start_val.type.width == 32):
                    start_val = self.builder.trunc(start_val, ir.IntType(32)) if isinstance(start_val.type, ir.IntType) else self.builder.fptosi(start_val, ir.IntType(32))
                if not (isinstance(end_val.type, ir.IntType) and end_val.type.width == 32):
                    end_val = self.builder.trunc(end_val, ir.IntType(32)) if isinstance(end_val.type, ir.IntType) else self.builder.fptosi(end_val, ir.IntType(32))

                # length do array fonte
                i8ptr = self.builder.bitcast(base_ptr, ir.IntType(8).as_pointer())
                base_i8 = self.builder.gep(i8ptr, [ir.Constant(ir.IntType(32), -8)])
                len_ptr = self.builder.bitcast(base_i8, ir.IntType(64).as_pointer())
                n64 = self.builder.load(len_ptr)
                n = self.builder.trunc(n64, ir.IntType(32))

                # clamp start/end: start = max(0, min(start, n)), end = max(0, min(end, n))
                zero = ir.Constant(ir.IntType(32), 0)
                # min(start, n)
                cmp_sn = self.builder.icmp_signed("<", start_val, n)
                start_min = self.builder.select(cmp_sn, start_val, n)
                # max(0, start_min)
                cmp_s0 = self.builder.icmp_signed("<", start_min, zero)
                start_cl = self.builder.select(cmp_s0, zero, start_min)

                cmp_en = self.builder.icmp_signed("<", end_val, n)
                end_min = self.builder.select(cmp_en, end_val, n)
                cmp_e0 = self.builder.icmp_signed("<", end_min, zero)
                end_cl = self.builder.select(cmp_e0, zero, end_min)

                # len = max(0, end - start)
                diff = self.builder.sub(end_cl, start_cl)
                cmp_d0 = self.builder.icmp_signed("<", diff, zero)
                slice_len = self.builder.select(cmp_d0, zero, diff)

                # Aloca novo array com mesmo tipo de elemento
                elem_ty = base_ptr.type.pointee
                # bytes por elemento
                if isinstance(elem_ty, ir.IntType):
                    elem_bytes = elem_ty.width // 8 if elem_ty.width >= 8 else 1
                elif isinstance(elem_ty, ir.DoubleType):
                    elem_bytes = 8
                elif isinstance(elem_ty, ir.FloatType):
                    elem_bytes = 4
                elif isinstance(elem_ty, ir.PointerType):
                    elem_bytes = 8
                else:
                    elem_bytes = 8
                elem_sz64 = ir.Constant(ir.IntType(64), elem_bytes)
                slice_len64 = self.builder.sext(slice_len, ir.IntType(64))
                data_bytes = self.builder.mul(slice_len64, elem_sz64)
                header_bytes = ir.Constant(ir.IntType(64), 8)
                total_bytes = self.builder.add(header_bytes, data_bytes)

                malloc = self._get_malloc()
                raw_ptr = self.builder.call(malloc, [total_bytes])  # i8*
                # grava header
                len_out_ptr = self.builder.bitcast(raw_ptr, ir.IntType(64).as_pointer())
                self.builder.store(slice_len64, len_out_ptr)
                # dest data ptr
                dest_i8 = self.builder.gep(raw_ptr, [ir.Constant(ir.IntType(32), 8)])
                dest_ptr = self.builder.bitcast(dest_i8, elem_ty.as_pointer())

                # src offset = base_ptr + start_cl
                src_elem_ptr = self.builder.gep(base_ptr, [start_cl])
                # memcpy(dest, src, bytes)
                memcpy = self._get_memcpy()
                src_i8 = self.builder.bitcast(src_elem_ptr, ir.IntType(8).as_pointer())
                _ = self.builder.call(memcpy, [dest_i8, src_i8, data_bytes])
                return dest_ptr

            # Acesso simples por índice
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

        elif isinstance(expr, LiteralTuple):
            # Representa tupla como struct alocado e retorna ponteiro
            elems = [self._gen_expr(e) for e in (expr.elementos or [])]
            elem_types = [v.type for v in elems]
            struct_ty = ir.LiteralStructType(elem_types)
            malloc = self._get_malloc()
            total_size = 0
            for t in elem_types:
                if isinstance(t, ir.IntType):
                    total_size += max(1, t.width // 8)
                elif isinstance(t, ir.DoubleType):
                    total_size += 8
                elif isinstance(t, ir.FloatType):
                    total_size += 4
                elif isinstance(t, ir.PointerType):
                    total_size += 8
                else:
                    total_size += 8
            raw = self.builder.call(malloc, [ir.Constant(ir.IntType(64), total_size)])
            tup_ptr = self.builder.bitcast(raw, struct_ty.as_pointer())
            for idx, val in enumerate(elems):
                field_ptr = self.builder.gep(tup_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), idx)])
                self.builder.store(val, field_ptr)
            return tup_ptr

        elif isinstance(expr, CriacaoClasse):
            # Cria instância de classe: aloca struct e inicializa
            class_name = expr.classe
            type_args = getattr(expr, 'type_args', None)
            
            # Se tem argumentos de tipo, instancia a classe genérica
            if type_args:
                class_name = self._instantiate_generic_class(expr.classe, tuple(type_args))
            
            if class_name not in self.classes:
                raise NameError(f"Classe '{class_name}' não declarada")
            
            struct_type, field_map = self.classes[class_name]
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
            # Enum: Cor.Verde -> constante i32
            if isinstance(expr.alvo, Variavel) and hasattr(self, 'enums') and expr.alvo.nome in self.enums:
                enum_map = self.enums[expr.alvo.nome]
                if expr.campo in enum_map:
                    return ir.Constant(ir.IntType(32), enum_map[expr.campo])
                raise AttributeError(f"Membro '{expr.campo}' inexistente no enum '{expr.alvo.nome}'")

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

    def _gen_foreach(self, node: InstrucaoLoopForEach):
        # Suporta range a..b e arrays (i32*)
        iterable = node.iterable
        # Range literal
        if isinstance(iterable, LiteralRange) or (isinstance(iterable, ExpressaoBinaria) and iterable.operador == ".."):
            # obtém início e fim
            if isinstance(iterable, LiteralRange):
                start_val = self._gen_expr(iterable.inicio)
                end_val = self._gen_expr(iterable.fim)
            else:
                start_val = self._gen_expr(iterable.esquerda)
                end_val = self._gen_expr(iterable.direita)
            # Normaliza para i32
            if not (isinstance(start_val.type, ir.IntType) and start_val.type.width == 32):
                start_val = self.builder.trunc(start_val, ir.IntType(32)) if isinstance(start_val.type, ir.IntType) else self.builder.fptosi(start_val, ir.IntType(32))
            if not (isinstance(end_val.type, ir.IntType) and end_val.type.width == 32):
                end_val = self.builder.trunc(end_val, ir.IntType(32)) if isinstance(end_val.type, ir.IntType) else self.builder.fptosi(end_val, ir.IntType(32))

            # i = start
            i_alloc = self.builder.alloca(ir.IntType(32), name="_it_i")
            self.builder.store(start_val, i_alloc)
            # variável iterada
            iter_alloc = self.builder.alloca(ir.IntType(32), name=node.iter_var)

            start_block = self.func.append_basic_block("foreach_start")
            body_block = self.func.append_basic_block("foreach_body")
            step_block = self.func.append_basic_block("foreach_step")
            end_block = self.func.append_basic_block("foreach_end")

            self.builder.branch(start_block)
            self.builder.position_at_end(start_block)
            i_val = self.builder.load(i_alloc)
            cond = self.builder.icmp_signed("<=", i_val, end_val)
            self.builder.cbranch(cond, body_block, end_block)

            # Corpo
            self.builder.position_at_end(body_block)
            # iter_var = i
            self.builder.store(i_val, iter_alloc)
            # Disponibiliza iter_var em symbols
            self.symbols[node.iter_var] = iter_alloc
            for s in node.corpo or []:
                self._gen_stmt(s)
                if self.builder.block.is_terminated:
                    break
            if not self.builder.block.is_terminated:
                self.builder.branch(step_block)

            # Step: i += 1
            self.builder.position_at_end(step_block)
            i_val2 = self.builder.load(i_alloc)
            i_next = self.builder.add(i_val2, ir.Constant(ir.IntType(32), 1))
            self.builder.store(i_next, i_alloc)
            if not self.builder.block.is_terminated:
                self.builder.branch(start_block)

            self.builder.position_at_end(end_block)
            return

        # Strings (i8*)
        str_ptr = self._gen_expr(iterable)
        if isinstance(str_ptr.type, ir.PointerType) and isinstance(str_ptr.type.pointee, ir.IntType) and str_ptr.type.pointee.width == 8:
            strlen = self._get_strlen()
            n64 = self.builder.call(strlen, [str_ptr])
            n = self.builder.trunc(n64, ir.IntType(32))

            idx_alloc = self.builder.alloca(ir.IntType(32), name="_it_idx")
            self.builder.store(ir.Constant(ir.IntType(32), 0), idx_alloc)
            ch_alloc = self.builder.alloca(ir.IntType(8), name=node.iter_var)
            self.symbols[node.iter_var] = ch_alloc

            start_block = self.func.append_basic_block("foreach_str_start")
            body_block = self.func.append_basic_block("foreach_str_body")
            step_block = self.func.append_basic_block("foreach_str_step")
            end_block = self.func.append_basic_block("foreach_str_end")

            self.builder.branch(start_block)
            self.builder.position_at_end(start_block)
            idx = self.builder.load(idx_alloc)
            cond = self.builder.icmp_signed("<", idx, n)
            self.builder.cbranch(cond, body_block, end_block)

            self.builder.position_at_end(body_block)
            ch_ptr = self.builder.gep(str_ptr, [idx])
            ch = self.builder.load(ch_ptr)
            self.builder.store(ch, ch_alloc)
            for s in node.corpo or []:
                self._gen_stmt(s)
                if self.builder.block.is_terminated:
                    break
            if not self.builder.block.is_terminated:
                self.builder.branch(step_block)

            self.builder.position_at_end(step_block)
            idx2 = self.builder.load(idx_alloc)
            idx_next = self.builder.add(idx2, ir.Constant(ir.IntType(32), 1))
            self.builder.store(idx_next, idx_alloc)
            if not self.builder.block.is_terminated:
                self.builder.branch(start_block)

            self.builder.position_at_end(end_block)
            return

        # Arrays tipados (elem*)
        arr_ptr = str_ptr  # já gerado; renome lógico
        if isinstance(arr_ptr.type, ir.PointerType) and not isinstance(arr_ptr.type.pointee, ir.LiteralStructType):
            # length pelo header
            i8ptr = self.builder.bitcast(arr_ptr, ir.IntType(8).as_pointer())
            base_i8 = self.builder.gep(i8ptr, [ir.Constant(ir.IntType(32), -8)])
            len_ptr = self.builder.bitcast(base_i8, ir.IntType(64).as_pointer())
            n64 = self.builder.load(len_ptr)
            n = self.builder.trunc(n64, ir.IntType(32))

            idx_alloc = self.builder.alloca(ir.IntType(32), name="_it_idx")
            self.builder.store(ir.Constant(ir.IntType(32), 0), idx_alloc)
            elem_ty = arr_ptr.type.pointee
            elem_alloc = self.builder.alloca(elem_ty, name=node.iter_var)
            self.symbols[node.iter_var] = elem_alloc

            start_block = self.func.append_basic_block("foreach_arr_start")
            body_block = self.func.append_basic_block("foreach_arr_body")
            step_block = self.func.append_basic_block("foreach_arr_step")
            end_block = self.func.append_basic_block("foreach_arr_end")

            self.builder.branch(start_block)
            self.builder.position_at_end(start_block)
            idx = self.builder.load(idx_alloc)
            cond = self.builder.icmp_signed("<", idx, n)
            self.builder.cbranch(cond, body_block, end_block)

            self.builder.position_at_end(body_block)
            elem_ptr = self.builder.gep(arr_ptr, [idx])
            elem = self.builder.load(elem_ptr)
            self.builder.store(elem, elem_alloc)
            for s in node.corpo or []:
                self._gen_stmt(s)
                if self.builder.block.is_terminated:
                    break
            if not self.builder.block.is_terminated:
                self.builder.branch(step_block)

            self.builder.position_at_end(step_block)
            idx2 = self.builder.load(idx_alloc)
            idx_next = self.builder.add(idx2, ir.Constant(ir.IntType(32), 1))
            self.builder.store(idx_next, idx_alloc)
            if not self.builder.block.is_terminated:
                self.builder.branch(start_block)

            self.builder.position_at_end(end_block)
            return

        raise NotImplementedError("foreach só suporta range a..b e arrays int por enquanto")

    # -------------------------
    # Monomorphization (Instanciação de Generics)
    # -------------------------
    def _instantiate_generic_function(self, func_name: str, type_args: Tuple[str, ...]) -> str:
        """Instancia uma versão concreta de uma função genérica com os tipos dados."""
        # Verifica se já foi instanciada
        key = (func_name, type_args)
        if key in self.instantiated_functions:
            return self.instantiated_functions[key]
        
        if func_name not in self.generic_functions:
            raise NameError(f"Função genérica '{func_name}' não encontrada")
        
        generic_decl = self.generic_functions[func_name]
        type_params = generic_decl.type_params or []
        
        if len(type_args) != len(type_params):
            raise TypeError(f"Função '{func_name}' espera {len(type_params)} argumentos de tipo, mas recebeu {len(type_args)}")
        
        # Cria mapeamento de parâmetros de tipo para tipos concretos
        type_map = dict(zip(type_params, type_args))
        
        # Nome mangled para a versão concreta
        mangled_name = f"{func_name}_{'_'.join(type_args)}"
        self.instantiated_functions[key] = mangled_name
        
        # Substitui tipos nos parâmetros e corpo
        concrete_params = []
        for pname, ptype in generic_decl.parametros or []:
            concrete_type = type_map.get(ptype, ptype)
            concrete_params.append((pname, concrete_type))
        
        concrete_ret_type = type_map.get(generic_decl.tipo_retorno, generic_decl.tipo_retorno)
        
        # Cria uma DeclaracaoFuncao concreta (sem type_params)
        from copy import deepcopy
        concrete_decl = DeclaracaoFuncao(
            mangled_name,
            concrete_params,
            generic_decl.corpo,  # Corpo será processado com type_map ativo
            generic_decl.is_procedure,
            concrete_ret_type,
            None  # sem type_params
        )
        
        # Guarda o mapeamento de tipos para uso durante geração do corpo
        prev_type_map = getattr(self, '_current_type_map', None)
        self._current_type_map = type_map
        
        # Gera a função concreta
        self._gen_function(concrete_decl)
        
        # Restaura mapeamento anterior
        self._current_type_map = prev_type_map
        
        return mangled_name
    
    def _instantiate_generic_class(self, class_name: str, type_args: Tuple[str, ...]) -> str:
        """Instancia uma versão concreta de uma classe genérica com os tipos dados."""
        # Verifica se já foi instanciada
        key = (class_name, type_args)
        if key in self.instantiated_classes:
            return self.instantiated_classes[key]
        
        if class_name not in self.generic_classes:
            raise NameError(f"Classe genérica '{class_name}' não encontrada")
        
        generic_decl = self.generic_classes[class_name]
        type_params = generic_decl.type_params or []
        
        if len(type_args) != len(type_params):
            raise TypeError(f"Classe '{class_name}' espera {len(type_params)} argumentos de tipo, mas recebeu {len(type_args)}")
        
        # Cria mapeamento de parâmetros de tipo para tipos concretos
        type_map = dict(zip(type_params, type_args))
        
        # Nome mangled para a versão concreta
        mangled_name = f"{class_name}_{'_'.join(type_args)}"
        self.instantiated_classes[key] = mangled_name
        
        # Substitui tipos nos campos
        concrete_fields = []
        for fname, ftype in generic_decl.campos:
            concrete_type = type_map.get(ftype, ftype)
            concrete_fields.append((fname, concrete_type))
        
        # Cria uma DeclaracaoClasse concreta (sem type_params)
        from copy import deepcopy
        concrete_decl = DeclaracaoClasse(
            mangled_name,
            concrete_fields,
            generic_decl.metodos,  # Métodos serão processados com type_map
            None  # sem type_params
        )
        
        # Guarda o mapeamento de tipos
        prev_type_map = getattr(self, '_current_type_map', None)
        self._current_type_map = type_map
        
        # Registra a classe concreta
        self._register_class(concrete_decl)
        
        # Gera métodos da classe concreta
        for metodo in generic_decl.metodos or []:
            # Substitui tipos nos parâmetros do método
            concrete_method_params = []
            for pname, ptype in metodo.parametros or []:
                concrete_type = type_map.get(ptype, ptype)
                concrete_method_params.append((pname, concrete_type))
            
            concrete_method_ret = type_map.get(metodo.tipo_retorno, metodo.tipo_retorno) if metodo.tipo_retorno else None
            
            concrete_method = DeclaracaoMetodo(
                mangled_name,  # classe concreta
                metodo.nome,
                concrete_method_params,
                metodo.corpo,
                metodo.is_procedure,
                concrete_method_ret,
                None  # sem type_params
            )
            self._gen_method(mangled_name, concrete_method)
        
        # Restaura mapeamento anterior
        self._current_type_map = prev_type_map
        
        return mangled_name

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

    def _gen_method(self, class_name: str, decl: DeclaracaoMetodo):
        prev_builder = self.builder
        prev_func = self.func
        prev_symbols = self.symbols

        try:
            if class_name not in self.classes:
                raise NameError(f"Classe '{class_name}' não registrada para método")
            class_ptr_ty = self.classes[class_name][0].as_pointer()

            param_types = [class_ptr_ty]
            param_names = ['self']
            for pname, ptype in (decl.parametros or []):
                param_types.append(self._type_from_name(ptype))
                param_names.append(pname)

            if decl.is_procedure or decl.tipo_retorno == 'void':
                ret_type = ir.VoidType()
            else:
                ret_type = self._type_from_name(decl.tipo_retorno)

            func_type = ir.FunctionType(ret_type, param_types)
            mangled = f"{class_name}_{decl.nome}"
            func = ir.Function(self.module, func_type, name=mangled)
            block = func.append_basic_block("entry")
            self.builder = ir.IRBuilder(block)
            self.func = func
            self.symbols = {}

            for idx, pname in enumerate(param_names):
                arg = func.args[idx]
                arg.name = pname
                alloca = self.builder.alloca(arg.type, name=pname)
                self.builder.store(arg, alloca)
                self.symbols[pname] = alloca

            for stmt in decl.corpo or []:
                self._gen_stmt(stmt)

            if not self.builder.block.is_terminated:
                if isinstance(ret_type, ir.VoidType):
                    self.builder.ret_void()
                elif isinstance(ret_type, ir.PointerType):
                    self.builder.ret(ir.Constant(ret_type, None))
                elif isinstance(ret_type, ir.DoubleType):
                    self.builder.ret(ir.Constant(ret_type, 0.0))
                else:
                    self.builder.ret(ir.Constant(ret_type, 0))
        finally:
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

    def _register_enum(self, decl: DeclaracaoEnum):
        # Enums armazenados como i32 com mapa de membros
        if not hasattr(self, 'enums'):
            self.enums: Dict[str, Dict[str,int]] = {}
        self.enums[decl.nome] = {nome: valor for (nome, valor) in decl.membros}

    def _type_from_name(self, type_name: str) -> ir.Type:
        """Helper para mapear nome de tipo para LLVM Type"""
        # Primeiro verifica se é um parâmetro de tipo genérico sendo substituído
        type_map = getattr(self, '_current_type_map', None)
        if type_map and type_name in type_map:
            # Recursivamente resolve o tipo concreto
            return self._type_from_name(type_map[type_name])
        
        if type_name in ('decimal', 'float', 'double'):
            return ir.DoubleType()
        elif type_name == 'string':
            return ir.IntType(8).as_pointer()
        elif type_name == 'bool':
            return ir.IntType(1)
        elif type_name == 'int':
            return ir.IntType(32)
        elif type_name in getattr(self, 'classes', {}):
            return self.classes[type_name][0].as_pointer()
        elif type_name in getattr(self, 'enums', {}):
            return ir.IntType(32)
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

    def _entry_alloca(self, ty: ir.Type, name: str):
        """Cria alloca no bloco de entrada da função atual para evitar problemas de dominância."""
        current_block = self.builder.block
        entry_block = self.func.entry_basic_block
        self.builder.position_at_start(entry_block)
        alloca = self.builder.alloca(ty, name=name)
        self.builder.position_at_end(current_block)
        return alloca

    def _builtin_input(self):
        """
        Implementa input() que lê uma linha do stdin e retorna string.
        Usa scanf com formato "%255[^\n]" para ler até a quebra de linha.
        """
        malloc = self._get_malloc()
        scanf = self._get_scanf()
        # Aloca buffer de 256 bytes
        buffer_size = ir.Constant(ir.IntType(64), 256)
        buffer = self.builder.call(malloc, [buffer_size])
        # Formato: lê até '\n', limitando a 255 chars
        fmt = self._gen_string("%255[^\n]")
        # Chama scanf(fmt, buffer)
        self.builder.call(scanf, [fmt, buffer])
        # Consome o '\n' restante, se existir
        fmt_nl = self._gen_string("%*c")
        self.builder.call(scanf, [fmt_nl])
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
        # Consome o '\n' após o número para não afetar próxima leitura
        fmt_nl = self._gen_string("%*c")
        self.builder.call(scanf, [fmt_nl])
        
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
