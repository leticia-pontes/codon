from .gerador_codigo import CodeGenerator as BytecodeGenerator
from .llvm_codegen import LLVMCodeGenerator

def get_codegen(target="bytecode"):
    if target == "llvm":
        return LLVMCodeGenerator()
    else:
        return BytecodeGenerator()
