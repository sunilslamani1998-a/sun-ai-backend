from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    score: float
    issues: tuple[str, ...]
    checks: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": list(self.issues),
            "checks": self.checks,
        }

def verify_response(
    response: str,
    original_prompt: str | None = None,
) -> VerificationResult:
    issues: list[str] = []
    cleaned_response = response.strip()

    nonempty = bool(cleaned_response)
    if not nonempty:
        issues.append("Response is empty.")

    reasonable_length = len(cleaned_response) <= 50000
    if not reasonable_length:
        issues.append("Response exceeds size limit.")

    no_obvious_placeholder = not bool(
        re.search(r"\b(TODO|PLACEHOLDER|INSERT_API_KEY_HERE)\b", cleaned_response, flags=re.IGNORECASE)
    )
    if not no_obvious_placeholder:
        issues.append("Response contains placeholder.")

    checks = {
        "nonempty": nonempty,
        "reasonable_length": reasonable_length,
        "no_obvious_placeholder": no_obvious_placeholder,
    }

    score = round(sum(checks.values()) / len(checks), 2)
    return VerificationResult(
        passed=all(checks.values()),
        score=score,
        issues=tuple(issues),
        checks=checks,
    )

def verify_code_text(code: str) -> VerificationResult:
    cleaned_code = code.strip()
    issues: list[str] = []
    nonempty = bool(cleaned_code)
    reasonable_length = len(cleaned_code) <= 100000
    checks = {
        "nonempty": nonempty,
        "reasonable_length": reasonable_length,
    }
    score = round(sum(checks.values()) / len(checks), 2)
    return VerificationResult(
        passed=all(checks.values()),
        score=score,
        issues=tuple(issues),
        checks=checks,
    )
