class BaseError(Exception):
    def __init__(self, message: str, line: int, col: int, code: str):
        self.message = message
        self.line = line
        self.col = col
        self.code = code
        super().__init__(f"{code}: {message} (Linha: {line}, Coluna: {col})")

class LexicalError(BaseError):
    def __init__(self, message: str, line: int, col: int, code: str = "LEX000"):
        super().__init__(message, line, col, code)

class SyntaxError(BaseError):
    def __init__(self, message: str, line: int, col: int, code: str = "SYN000"):
        super().__init__(message, line, col, code)

class SemanticError(BaseError):
    def __init__(self, message: str, line: int, col: int, code: str = "SEM000"):
        super().__init__(message, line, col, code)

class ErrorHandler:
    def __init__(self):
        self.errors = []

    def report_error(self, error: BaseError):
        self.errors.append(error)
        print(error)

    def has_errors(self) -> bool:
        return bool(self.errors)