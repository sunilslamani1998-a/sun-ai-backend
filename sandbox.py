from __future__ import annotations
import ast
from dataclasses import dataclass
from typing import Any
MAX_CODE_LENGTH = 100000

@dataclass(frozen=True)
class CodeValidationResult:
    valid: bool
    error: str | None = None
    line: int | None = None
    column: int | None = None
    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "error": self.error, "line": self.line, "column": self.column}

def validate_python_code(code: str) -> CodeValidationResult:
    if not isinstance(code, str):
        return CodeValidationResult(False, "Code must be a string.")
    if not code.strip():
        return CodeValidationResult(False, "Code cannot be empty.")
    if len(code) > MAX_CODE_LENGTH:
        return CodeValidationResult(False, "Code exceeds the maximum allowed length.")
    try:
        ast.parse(code)
        return CodeValidationResult(True)
    except SyntaxError as exc:
        return CodeValidationResult(False, exc.msg, exc.lineno, exc.offset)
    except (ValueError, TypeError, MemoryError) as exc:
        return CodeValidationResult(False, f"Unable to parse code: {type(exc).__name__}")

def validate_python_file_text(filename: str, code: str) -> CodeValidationResult:
    if not filename.endswith(".py"):
        return CodeValidationResult(False, "Only Python source filenames are accepted.")
    return validate_python_code(code)
