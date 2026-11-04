from __future__ import annotations
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
import database
from sandbox import validate_python_code
ALLOWED_TARGET_FILES = frozenset({"agent.py", "memory.py", "learning.py", "verification.py", "sandbox.py", "bittu.py", "main.py", "database.py", "security.py", "config.py"})

@dataclass(frozen=True)
class ProposalResult:
    success: bool
    proposal_id: int | None = None
    error: str | None = None
    validation: dict[str, Any] | None = None
    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "proposal_id": self.proposal_id, "error": self.error, "validation": self.validation}

def normalize_target_file(target_file: str) -> str:
    if not isinstance(target_file, str):
        raise ValueError("Target filename must be a string.")
    cleaned = target_file.strip().replace("\\", "/")
    if not cleaned:
        raise ValueError("Target filename cannot be empty.")
    path = PurePosixPath(cleaned)
    if path.is_absolute() or len(path.parts) != 1 or path.name != cleaned:
        raise ValueError("Only project-root filenames are allowed.")
    if cleaned not in ALLOWED_TARGET_FILES:
        raise ValueError("Target file is not in the improvement allowlist.")
    return cleaned

def validate_proposed_code(target_file: str, proposed_code: str) -> dict[str, Any]:
    target = normalize_target_file(target_file)
    if not isinstance(proposed_code, str):
        return {"valid": False, "error": "Proposed code must be a string."}
    if not proposed_code.strip():
        return {"valid": False, "error": "Proposed code cannot be empty."}
    if len(proposed_code) > 100000:
        return {"valid": False, "error": "Proposed code is too large."}
    if target.endswith(".py"):
        return validate_python_code(proposed_code).to_dict()
    return {"valid": True, "error": None, "note": "Text validation only; no security analysis performed."}

def create_improvement_proposal(user_id: str, title: str, description: str, target_file: str, proposed_code: str) -> ProposalResult:
    title, description = title.strip(), description.strip()
    if not title:
        return ProposalResult(False, error="Proposal title cannot be empty.")
    if not description:
        return ProposalResult(False, error="Proposal description cannot be empty.")
    if len(title) > 200:
        return ProposalResult(False, error="Proposal title is too long.")
    if len(description) > 12000:
        return ProposalResult(False, error="Proposal description is too long.")
    try:
        target = normalize_target_file(target_file)
    except ValueError as exc:
        return ProposalResult(False, error=str(exc))
    validation = validate_proposed_code(target, proposed_code)
    if not validation.get("valid"):
        return ProposalResult(False, error="Proposed code failed validation.", validation=validation)
    try:
        pid = database.add_code_proposal(user_id, title, description, target, proposed_code, "Syntax validation passed; isolated tests not run.")
    except Exception:
        return ProposalResult(False, error="Unable to save the proposal.", validation=validation)
    return ProposalResult(True, proposal_id=pid, validation=validation)

def list_improvement_proposals(user_id: str, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    return database.get_code_proposals(user_id, status, limit)

def update_proposal_status(user_id: str, proposal_id: int, status: str, test_result: str | None = None) -> bool:
    return database.update_code_proposal_status(user_id, proposal_id, status, test_result)
