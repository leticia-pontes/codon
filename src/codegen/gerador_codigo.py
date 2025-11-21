from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from llvmlite import ir
from src.parser.ast.ast_base import *

@dataclass
class Escopo:
    vars: Dict[str, ir.Value] = field(default_factory=dict)

class ContextoGeracao:
    def __init__(self, nome_modulo: str = "codon_module"):
        self.module = ir.Module(name=nome_modulo)
        self.double_t = ir.DoubleType()
        self.i32_t = ir.IntType(32)
        self.i64_t = ir.IntType(64)
        self.bool_t = ir.IntType(1)
        self.void_t = ir.VoidType()
        self.char_t = ir.IntType(8)
        self.string_t = ir.PointerType(self.char_t)
        self.function: Optional[ir.Function] = None
        self.builder: Optional[ir.IRBuilder] = None
        self.scopes: List[Escopo] = []
        self.classes_types: Dict[str, ir.Type] = {}

    def push_scope(self) -> None:
        self.scopes.append(Escopo())

    def pop_scope(self) -> None:
        self.scopes.pop()

    def current_scope(self) -> Escopo:
        if not self.scopes: self.push_scope()
        return self.scopes[-1]

    def bind_name(self, name: str, ptr: ir.Value) -> None:
        self.current_scope().vars[name] = ptr

    def lookup_name(self, name: str) -> Optional[ir.Value]:
        for escopo in reversed(self.scopes):
            if name in escopo.vars: return escopo.vars[name]
        return None

    def enter_function(self, fn: ir.Function) -> None:
        self.function = fn
        entry = fn.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.scopes = []
        self.push_scope()

    def leave_function(self) -> None:
        self.function = None
        self.builder = None
        self.scopes = []

    def create_local(self, name: str, llvm_type: ir.Type) -> ir.AllocaInstr:
        entry = self.function.entry_basic_block
        if self.builder.block == entry:
            return self.builder.alloca(llvm_type, name=name)
        current = self.builder.block
        self.builder.position_at_start(entry)
        alloca = self.builder.alloca(llvm_type, name=name)
        self.builder.position_at_end(current)
        self.bind_name(name, alloca)
        return alloca

class CodeGenerator:
    def __init__(self):
        self.ctx = ContextoGeracao()
        self.funcoes: Dict[str, ir.Function] = {}
        self.printf_fn = None
        self._setup_runtime()

    def _setup_runtime(self):
        fmt_ty = ir.FunctionType(self.ctx.i32_t, [self.ctx.string_t], var_arg=True)
        self.printf_fn = ir.Function(self.ctx.module, fmt_ty, name="printf")

    def _mapear_tipo(self, tipo_str: str) -> ir.Type:
        base = tipo_str.replace("[]", "").strip()
        if base in ('int', 'i32'): return self.ctx.i32_t
        if base in ('float', 'double', 'any'): return self.ctx.double_t
        if base in ('bool', 'boolean'): return self.ctx.bool_t
        if base in ('string', 'dna', 'prot', 'rna', 'char'): return self.ctx.string_t
        if base == 'void': return self.ctx.void_t
        if base in self.ctx.classes_types: return self.ctx.classes_types[base]
        return self.ctx.double_t

    def generate(self, programa: Programa) -> ir.Module:
        for decl in programa.declaracoes:
            if isinstance(decl, DeclaracaoClasse):
                self._declarar_classe(decl)
        for decl in programa.declaracoes:
            if isinstance(decl, DeclaracaoVariavel):
                self._codegen_global_var(decl)
        for decl in programa.declaracoes:
            if isinstance(decl, DeclaracaoFuncao):
                self._declarar_proto_funcao(decl)
        for decl in programa.declaracoes:
            if isinstance(decl, DeclaracaoFuncao):
                self._definir_corpo_funcao(decl)
        self._gerar_main_implicita(programa.declaracoes)
        return self.ctx.module

    def _declarar_classe(self, node: DeclaracaoClasse):
        element_types = []
        if node.campos:
            for _, tipo_campo in node.campos:
                element_types.append(self._mapear_tipo(tipo_campo))
        if not element_types:
            element_types = [self.ctx.i32_t]
        struct_ty = ir.LiteralStructType(element_types)
        self.ctx.classes_types[node.nome] = struct_ty

    def _codegen_global_var(self, node: DeclaracaoVariavel):
        typ = self._mapear_tipo(node.tipo)
        gvar = ir.GlobalVariable(self.ctx.module, typ, name=node.nome)
        if typ == self.ctx.double_t: gvar.initializer = ir.Constant(typ, 0.0)
        elif typ == self.ctx.i32_t: gvar.initializer = ir.Constant(typ, 0)
        elif typ == self.ctx.string_t: gvar.initializer = ir.Constant(typ, None)
        else: gvar.initializer = ir.Constant(typ, 0)

    def _declarar_proto_funcao(self, node: DeclaracaoFuncao):
        param_types = []
        param_names = []
        for p in node.parametros:
            if ':' in p:
                nm, tp = p.split(':')
                param_names.append(nm.strip())
                param_types.append(self._mapear_tipo(tp.strip()))
            else:
                param_names.append(p.strip())
                param_types.append(self.ctx.double_t)
        ret_type = self._mapear_tipo(node.tipo_retorno)
        fnty = ir.FunctionType(ret_type, param_types)
        fn = ir.Function(self.ctx.module, fnty, name=node.nome)
        for i, arg in enumerate(fn.args):
            arg.name = param_names[i]
        self.funcoes[node.nome] = fn

    def _definir_corpo_funcao(self, node: DeclaracaoFuncao):
        fn = self.funcoes[node.nome]
        self.ctx.enter_function(fn)
        for i, arg in enumerate(fn.args):
            alloca = self.ctx.create_local(arg.name, arg.type)
            self.ctx.builder.store(arg, alloca)
        for stmt in node.corpo:
            self._codegen_stmt(stmt)
        if not self.ctx.builder.block.is_terminated:
            if isinstance(fn.function_type.return_type, ir.VoidType):
                self.ctx.builder.ret_void()
            else:
                self.ctx.builder.ret(ir.Constant(fn.function_type.return_type, 0))
        self.ctx.leave_function()

    def _gerar_main_implicita(self, decls: List[ASTNode]):
        if 'main' in self.funcoes: return
        stmts_soltos = [d for d in decls if not isinstance(d, (DeclaracaoFuncao, DeclaracaoClasse))]
        vars_com_init = [d for d in decls if isinstance(d, DeclaracaoVariavel) and d.valor]
        if not stmts_soltos and not vars_com_init: return
        fnty = ir.FunctionType(self.ctx.i32_t, [])
        main_fn = ir.Function(self.ctx.module, fnty, name="main")
        self.ctx.enter_function(main_fn)
        for v in vars_com_init:
            val = self._codegen_expr(v.valor)
            gvar = self.ctx.module.get_global(v.nome)
            if gvar:
                val = self._cast(val, gvar.type.pointee)
                self.ctx.builder.store(val, gvar)
        for stmt in stmts_soltos:
            if not isinstance(stmt, DeclaracaoVariavel):
                self._codegen_stmt(stmt)
        self.ctx.builder.ret(ir.Constant(self.ctx.i32_t, 0))
        self.ctx.leave_function()

    def _codegen_stmt(self, node: ASTNode):
        if isinstance(node, InstrucaoImpressao):
            val = self._codegen_expr(node.expressao)
            self._emit_print(val)
        elif isinstance(node, InstrucaoAtribuicao):
            val = self._codegen_expr(node.valor)
            if isinstance(node.alvo, Variavel):
                ptr = self._resolve_ptr(node.alvo.nome)
                if ptr:
                    val = self._cast(val, ptr.type.pointee)
                    self.ctx.builder.store(val, ptr)
        elif isinstance(node, InstrucaoIf):
            cond = self._codegen_expr(node.condicao)
            cond = self._to_bool(cond)
            with self.ctx.builder.if_else(cond) as (then, otherwise):
                with then:
                    for s in node.bloco_if: self._codegen_stmt(s)
                with otherwise:
                    for s in node.bloco_else: self._codegen_stmt(s)
        elif isinstance(node, InstrucaoLoopWhile):
            w_cond = self.ctx.builder.append_basic_block("while_cond")
            w_body = self.ctx.builder.append_basic_block("while_body")
            w_end = self.ctx.builder.append_basic_block("while_end")
            self.ctx.builder.branch(w_cond)
            with self.ctx.builder.goto_block(w_cond):
                c = self._codegen_expr(node.condicao)
                c = self._to_bool(c)
                self.ctx.builder.cbranch(c, w_body, w_end)
            with self.ctx.builder.goto_block(w_body):
                for s in node.corpo: self._codegen_stmt(s)
                self.ctx.builder.branch(w_cond)
            self.ctx.builder.position_at_end(w_end)
        elif isinstance(node, InstrucaoRetorno):
            if node.expressao:
                val = self._codegen_expr(node.expressao)
                ret_ty = self.ctx.function.function_type.return_type
                val = self._cast(val, ret_ty)
                self.ctx.builder.ret(val)
            else: self.ctx.builder.ret_void()
        elif isinstance(node, InstrucaoExpressao):
            if node.expressao: self._codegen_expr(node.expressao)
        elif isinstance(node, DeclaracaoVariavel):
            typ = self._mapear_tipo(node.tipo)
            alloca = self.ctx.create_local(node.nome, typ)
            if node.valor:
                val = self._codegen_expr(node.valor)
                val = self._cast(val, typ)
                self.ctx.builder.store(val, alloca)

    def _codegen_expr(self, node: ASTNode) -> ir.Value:
        if isinstance(node, Literal):
            tipo_lit = getattr(node, 'tipo_literal', None)
            if tipo_lit in ('dna', 'prot', 'rna'):
                return self._create_string_literal(node.valor)
            if isinstance(node.valor, str):
                return self._create_string_literal(node.valor)
            if isinstance(node.valor, bool):
                return ir.Constant(self.ctx.bool_t, 1 if node.valor else 0)
            if isinstance(node.valor, int):
                return ir.Constant(self.ctx.i32_t, node.valor)
            if isinstance(node.valor, float):
                return ir.Constant(self.ctx.double_t, node.valor)
            return ir.Constant(self.ctx.double_t, 0.0)
        elif isinstance(node, Variavel):
            ptr = self._resolve_ptr(node.nome)
            if ptr: return self.ctx.builder.load(ptr, name=node.nome)
            return ir.Constant(self.ctx.double_t, 0.0)
        elif isinstance(node, ExpressaoBinaria):
            lhs = self._codegen_expr(node.esquerda)
            rhs = self._codegen_expr(node.direita)
            op = node.operador
            lhs = self._cast(lhs, self.ctx.double_t)
            rhs = self._cast(rhs, self.ctx.double_t)
            if op == '+': return self.ctx.builder.fadd(lhs, rhs)
            if op == '-': return self.ctx.builder.fsub(lhs, rhs)
            if op == '*': return self.ctx.builder.fmul(lhs, rhs)
            if op == '/': return self.ctx.builder.fdiv(lhs, rhs)
            if op == '==': return self.ctx.builder.fcmp_ordered('==', lhs, rhs)
            if op == '<': return self.ctx.builder.fcmp_ordered('<', lhs, rhs)
            if op == '>': return self.ctx.builder.fcmp_ordered('>', lhs, rhs)
            return lhs
        elif isinstance(node, ChamadaFuncao):
            if node.nome.nome in self.funcoes:
                fn = self.funcoes[node.nome.nome]
                args = [self._codegen_expr(a) for a in node.argumentos]
                casted_args = []
                for i, arg in enumerate(args):
                    if i < len(fn.args):
                        casted_args.append(self._cast(arg, fn.args[i].type))
                    else: casted_args.append(arg)
                return self.ctx.builder.call(fn, casted_args)
            return ir.Constant(self.ctx.double_t, 0.0)
        elif isinstance(node, CriacaoArray):
            return ir.Constant(self.ctx.string_t, None)
        return ir.Constant(self.ctx.double_t, 0.0)

    def _resolve_ptr(self, name: str):
        local = self.ctx.lookup_name(name)
        if local: return local
        if name in self.ctx.module.globals: return self.ctx.module.get_global(name)
        return None

    def _create_string_literal(self, s: str) -> ir.Value:
        s_bytes = s.encode('utf-8') + b'\0'
        c_str = ir.Constant(ir.ArrayType(self.ctx.char_t, len(s_bytes)), bytearray(s_bytes))
        global_var = ir.GlobalVariable(self.ctx.module, c_str.type, name=f".str_{hash(s)}")
        global_var.linkage = 'internal'
        global_var.global_constant = True
        global_var.initializer = c_str
        return self.ctx.builder.bitcast(global_var, self.ctx.string_t)

    def _cast(self, val: ir.Value, target_ty: ir.Type) -> ir.Value:
        if val.type == target_ty: return val
        if isinstance(val.type, ir.IntType) and isinstance(target_ty, ir.DoubleType):
            return self.ctx.builder.sitofp(val, target_ty)
        if isinstance(val.type, ir.DoubleType) and isinstance(target_ty, ir.IntType):
            return self.ctx.builder.fptosi(val, target_ty)
        if val.type == self.ctx.bool_t and target_ty == self.ctx.i32_t:
            return self.ctx.builder.zext(val, target_ty)
        return val

    def _to_bool(self, val: ir.Value) -> ir.Value:
        if val.type == self.ctx.bool_t: return val
        if isinstance(val.type, ir.IntType):
            return self.ctx.builder.icmp_signed('!=', val, ir.Constant(val.type, 0))
        if isinstance(val.type, ir.DoubleType):
            return self.ctx.builder.fcmp_ordered('!=', val, ir.Constant(val.type, 0.0))
        return ir.Constant(self.ctx.bool_t, 1)

    def _emit_print(self, val: ir.Value):
        if val.type == self.ctx.string_t:
            fmt = self._create_string_literal("%s\n")
        elif isinstance(val.type, ir.IntType):
            fmt = self._create_string_literal("%d\n")
        else:
            fmt = self._create_string_literal("%f\n")
            if val.type != self.ctx.double_t:
                val = self._cast(val, self.ctx.double_t)
        self.ctx.builder.call(self.printf_fn, [fmt, val])