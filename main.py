
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import database
import learning
import memory
import self_improve
from agent import (
    AgentConfigurationError,
    AgentRequestError,
    ask_ai,
)
from config import settings
from security import AuthenticatedUser
from verification import verify_response


# -------------------------------------------------------------------
# Application lifecycle
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""
    database.init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="SUN.AI Advanced personal AI assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)


# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------
#
# For production, replace the wildcard with the exact frontend origin.
# CORS is not authentication and does not protect the API token.
# -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


# -------------------------------------------------------------------
# Request models
# -------------------------------------------------------------------

class ChatRequest(BaseModel):
    prompt: str = Field(
        min_length=1,
        max_length=12000,
    )


class MemoryCreateRequest(BaseModel):
    content: str = Field(
        min_length=1,
        max_length=12000,
    )
    category: str = Field(
        default="general",
        max_length=64,
    )
    importance: int = Field(
        default=1,
        ge=1,
        le=5,
    )


class FeedbackRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=12000,
    )
    rating: int = Field(
        ge=1,
        le=5,
    )
    details: str | None = Field(
        default=None,
        max_length=12000,
    )


class LearningRecordRequest(BaseModel):
    topic: str = Field(
        min_length=1,
        max_length=200,
    )
    summary: str = Field(
        min_length=1,
        max_length=12000,
    )
    source: str | None = Field(
        default=None,
        max_length=1000,
    )


class ImprovementProposalRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )
    description: str = Field(
        min_length=1,
        max_length=12000,
    )
    target_file: str = Field(
        min_length=1,
        max_length=255,
    )
    proposed_code: str = Field(
        min_length=1,
        max_length=100000,
    )


class ProposalStatusRequest(BaseModel):
    status: str = Field(
        min_length=1,
        max_length=32,
    )
    test_result: str | None = Field(
        default=None,
        max_length=12000,
    )


# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, Any]:
    """Return application and database health."""
    database_ok = database.check_database()

    return {
        "status": "ok" if database_ok else "degraded",
        "database": "connected" if database_ok else "unavailable",
        "app": settings.app_name,
        "version": "0.1.0",
    }


# -------------------------------------------------------------------
# Chat
# -------------------------------------------------------------------

@app.post("/api/chat")
async def chat(
    body: ChatRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Send a prompt to Gemini with relevant memory and learning context."""
    cleaned_prompt = body.prompt.strip()

    if not cleaned_prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prompt cannot be empty.",
        )

    memory_context = memory.build_memory_context(
        user_id=user_id,
        query=cleaned_prompt,
        limit=8,
    )

    learning_context = learning.build_learning_context(
        user_id=user_id,
        limit=5,
    )

    try:
        response = await ask_ai(
            prompt=cleaned_prompt,
            memories=memory_context,
            learning_context=learning_context,
        )

    except AgentConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except AgentRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    verification = verify_response(
        response=response,
        original_prompt=cleaned_prompt,
    )

    return {
        "response": response,
        "verification": verification.to_dict(),
        "memory_used": len(memory_context),
        "learning_records_used": len(learning_context),
    }


# -------------------------------------------------------------------
# Memory
# -------------------------------------------------------------------

@app.post("/api/memory")
async def create_memory(
    body: MemoryCreateRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Create a memory."""
    try:
        memory_id = memory.save_memory(
            user_id=user_id,
            content=body.content,
            category=body.category,
            importance=body.importance,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "memory_id": memory_id,
    }


@app.get("/api/memory")
async def list_memory(
    user_id: AuthenticatedUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """List stored memories."""
    items = memory.list_memories(
        user_id=user_id,
        limit=limit,
    )

    return {
        "count": len(items),
        "memories": items,
    }


@app.get("/api/memory/search")
async def search_memory(
    user_id: AuthenticatedUser,
    q: str = Query(min_length=1, max_length=1000),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """Search stored memories."""
    items = memory.search_memories(
        user_id=user_id,
        query=q,
        limit=limit,
    )

    return {
        "count": len(items),
        "memories": items,
    }


@app.delete("/api/memory/{memory_id}")
async def remove_memory(
    memory_id: int,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Delete one memory."""
    deleted = memory.delete_user_memory(
        user_id=user_id,
        memory_id=memory_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found.",
        )

    return {
        "success": True,
        "deleted": True,
    }


@app.delete("/api/memory")
async def remove_all_memory(
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Delete all memories for the authenticated user."""
    deleted_count = memory.clear_user_memories(
        user_id=user_id,
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
    }


# -------------------------------------------------------------------
# Feedback
# -------------------------------------------------------------------

@app.post("/api/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Record user feedback."""
    try:
        feedback_id = learning.record_feedback(
            user_id=user_id,
            message=body.message,
            rating=body.rating,
            details=body.details,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "feedback_id": feedback_id,
    }


@app.get("/api/feedback")
async def list_feedback(
    user_id: AuthenticatedUser,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Retrieve feedback history."""
    items = learning.get_feedback_history(
        user_id=user_id,
        limit=limit,
    )

    return {
        "count": len(items),
        "feedback": items,
    }


@app.get("/api/learning")
async def learning_summary(
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Return feedback statistics and saved learning records."""
    return {
        "feedback_summary": learning.summarize_feedback(
            user_id=user_id,
        ),
        "learning_records": learning.get_learning_history(
            user_id=user_id,
        ),
    }


@app.post("/api/learning")
async def create_learning_record(
    body: LearningRecordRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Save a learning record."""
    try:
        record_id = learning.save_learning_record(
            user_id=user_id,
            topic=body.topic,
            summary=body.summary,
            source=body.source,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "learning_record_id": record_id,
    }


# -------------------------------------------------------------------
# Improvement proposals
# -------------------------------------------------------------------

@app.post("/api/improvements/propose")
async def propose_improvement(
    body: ImprovementProposalRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Create a validated code improvement proposal."""
    result = self_improve.create_improvement_proposal(
        user_id=user_id,
        title=body.title,
        description=body.description,
        target_file=body.target_file,
        proposed_code=body.proposed_code,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.to_dict(),
        )

    return result.to_dict()


@app.get("/api/improvements")
async def list_improvements(
    user_id: AuthenticatedUser,
    proposal_status: str | None = Query(
        default=None,
        alias="status",
        max_length=32,
    ),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """List code improvement proposals."""
    proposals = self_improve.list_improvement_proposals(
        user_id=user_id,
        status=proposal_status,
        limit=limit,
    )

    return {
        "count": len(proposals),
        "proposals": proposals,
    }


@app.patch("/api/improvements/{proposal_id}")
async def update_improvement(
    proposal_id: int,
    body: ProposalStatusRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Update a proposal's review status."""
    try:
        updated = self_improve.update_proposal_status(
            user_id=user_id,
            proposal_id=proposal_id,
            status=body.status,
            test_result=body.test_result,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found.",
        )

    return {
        "success": True,
        "proposal_id": proposal_id,
        "status": body.status,
    }
