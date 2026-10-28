from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

import database
from sandbox import validate_python_code

ALLOWED_TARGET_FILES = frozenset(
    {
        "agent.py",
        "memory.py",
        "learning.py",
        "verification.py",
        "sandbox.py",
        "bittu.py",
        "main.py",
        "database.py",
        "security.py",
        "config.py",
    }
)

@dataclass(frozen=True)
class ProposalResult:
    success: bool
    proposal_id: int | None = None
    error: str | None = None
    validation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "proposal_id": self.proposal_id,
            "error": self.error,
            "validation": self.validation,
        }

def normalize_target_file(target_file: str) -> str:
    cleaned = target_file.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if path.is_absolute() or len(path.parts) != 1 or path.name != cleaned:
        raise ValueError("Invalid target filename.")
    if cleaned not in ALLOWED_TARGET_FILES:
        raise ValueError("Target file is not in the improvement allowlist.")
    return cleaned

def validate_proposed_code(target_file: str, proposed_code: str) -> dict[str, Any]:
    normalized_target = normalize_target_file(target_file)
    if not isinstance(proposed_code, str) or not proposed_code.strip():
        return {"valid": False, "error": "Proposed code must be a non-empty string."}
    if normalized_target.endswith(".py"):
        return validate_python_code(proposed_code).to_dict()
    return {"valid": True, "error": None}

def create_improvement_proposal(
    user_id: str,
    title: str,
    description: str,
    target_file: str,
    proposed_code: str,
) -> ProposalResult:
    try:
        normalized_target = normalize_target_file(target_file)
    except ValueError as exc:
        return ProposalResult(success=False, error=str(exc))

    validation = validate_proposed_code(target_file=normalized_target, proposed_code=proposed_code)
    if not validation.get("valid", False):
        return ProposalResult(success=False, error="Failed validation.", validation=validation)

    proposal_id = database.add_code_proposal(
        user_id=user_id,
        title=title.strip(),
        description=description.strip(),
        target_file=normalized_target,
        proposed_code=proposed_code,
        test_result="Syntax validation passed.",
    )
    return ProposalResult(success=True, proposal_id=proposal_id, validation=validation)

def list_improvement_proposals(user_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return database.get_code_proposals(user_id=user_id, status=status, limit=limit)

def update_proposal_status(user_id: str, proposal_id: int, status: str, test_result: str | None = None) -> bool:
    return database.update_code_proposal_status(user_id=user_id, proposal_id=proposal_id, status=status, test_result=test_result)
