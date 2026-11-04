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
        return {"passed": self.passed, "score": self.score, "issues": list(self.issues), "checks": self.checks}

def verify_response(response: str, original_prompt: str | None = None) -> VerificationResult:
    issues = []
    response = response.strip()
    checks = {"nonempty": bool(response), "reasonable_length": len(response) <= 50000,
              "no_obvious_placeholder": not bool(re.search(r"\b(TODO|PLACEHOLDER|INSERT_API_KEY_HERE)\b", response, re.I)),
              "prompt_present": original_prompt is None or bool(original_prompt.strip())}
    for name, passed in checks.items():
        if not passed:
            issues.append({"nonempty": "Response is empty.", "reasonable_length": "Response exceeds the configured size limit.",
                           "no_obvious_placeholder": "Response contains an obvious placeholder.", "prompt_present": "Original prompt is empty."}[name])
    return VerificationResult(all(checks.values()), round(sum(checks.values()) / len(checks), 2), tuple(issues), checks)

def verify_code_text(code: str) -> VerificationResult:
    code = code.strip()
    checks = {"nonempty": bool(code), "reasonable_length": len(code) <= 100000,
              "no_obvious_placeholder": not bool(re.search(r"\b(TODO|INSERT_API_KEY_HERE)\b", code, re.I))}
    issues = []
    for name, passed in checks.items():
        if not passed:
            issues.append({"nonempty": "Code is empty.", "reasonable_length": "Code exceeds the configured size limit.", "no_obvious_placeholder": "Code contains an obvious placeholder."}[name])
    return VerificationResult(all(checks.values()), round(sum(checks.values()) / len(checks), 2), tuple(issues), checks)
