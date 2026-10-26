def verify_result(result: str) -> dict:
    if not isinstance(result, str):
        return {
            "passed": False,
            "reason": "Result must be text.",
        }

    if not result.strip():
        return {
            "passed": False,
            "reason": "The result is empty.",
        }

    return {
        "passed": True,
        "reason": "Non-empty text result received.",
        "note": (
            "This is a basic validation only. "
            "It does not establish factual correctness."
        ),
    }
