from . import ast_base as _ast_base

__all__ = list(_ast_base.__all__)
globals().update({name: getattr(_ast_base, name) for name in __all__})