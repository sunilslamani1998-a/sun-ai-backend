import uuid
from pathlib import Path

from database import connect_db
from sandbox import check_python_syntax

ALLOWED_FILES = {
    "agent.py",
    "memory.py",
    "learning.py",
    "verification.py",
}


def propose_change(
    user_id: str,
    filename: str,
    proposed_content: str,
) -> dict:
    if filename not in ALLOWED_FILES:
        raise ValueError("This file is not eligible for modification.")

    if len(proposed_content) > 100_000:
        raise ValueError("Proposal exceeds the size limit.")

    if filename.endswith(".py"):
        check = check_python_syntax(proposed_content)
        if not check["passed"]:
            raise ValueError(f"Syntax check failed: {check['error']}")

    proposal_id = str(uuid.uuid4())

    with connect_db() as db:
        db.execute(
            """
            INSERT INTO code_proposals
                (id, user_id, filename, proposed_content, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (proposal_id, user_id, filename, proposed_content),
        )

    return {
        "id": proposal_id,
        "filename": filename,
        "status": "pending",
        "message": (
            "Proposal saved. Review and test it before applying "
            "the change manually."
        ),
    }


def list_proposals(user_id: str):
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT id, filename, status, created_at
            FROM code_proposals
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]
