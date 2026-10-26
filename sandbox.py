import ast


def check_python_syntax(source: str) -> dict:
    if len(source) > 100_000:
        return {
            "passed": False,
            "error": "Source exceeds the 100 KB limit.",
        }

    try:
        ast.parse(source)
        return {
            "passed": True,
            "message": "Python syntax is valid.",
        }
    except SyntaxError as exc:
        return {
            "passed": False,
            "error": str(exc),
            "line": exc.lineno,
        }
