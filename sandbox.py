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
        return {
            "valid": self.valid,
            "error": self.error,
            "line": self.line,
            "column": self.column,
        }

def validate_python_code(code: str) -> CodeValidationResult:
    if not isinstance(code, str):
        return CodeValidationResult(valid=False, error="Code must be a string.")
    if not code.strip():
        return CodeValidationResult(valid=False, error="Code cannot be empty.")
    if len(code) > MAX_CODE_LENGTH:
        return CodeValidationResult(valid=False, error="Code exceeds maximum length.")

    try:
        ast.parse(code)
        return CodeValidationResult(valid=True)
    except SyntaxError as exc:
        return CodeValidationResult(
            valid=False,
            error=exc.msg,
            line=exc.lineno,
            column=exc.offset,
        )
    except (ValueError, TypeError, MemoryError) as exc:
        return CodeValidationResult(valid=False, error=f"Parse error: {type(exc).__name__}")
