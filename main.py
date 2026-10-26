import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field

from database import init_db, health_check
from security import require_auth
from memory import save_memory, search_memory, delete_memory
from learning import record_feedback, get_learning_summary
from agent import ask_ai
from verification import verify_result
from self_improve import propose_change, list_proposals

logging.basicConfig(level="INFO")
logger = logging.getLogger("sunai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SUN.AI Advanced",
    version="2.0.0",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class FeedbackRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    response: str = Field(min_length=1, max_length=20000)
    rating: int = Field(ge=1, le=5)
    notes: str = Field(default="", max_length=2000)


class ProposalRequest(BaseModel):
    filename: str
    proposed_content: str = Field(min_length=1, max_length=100000)


@app.get("/health")
def health():
    try:
        return {
            "status": "ok" if health_check() else "degraded",
            "database": "connected",
        }
    except Exception:
        logger.exception("Health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/api/chat")
async def chat(
    body: ChatRequest,
    user_id: str = Depends(require_auth),
):
    memories = search_memory(user_id, body.prompt)
    try:
        answer = await ask_ai(
            body.prompt,
            [m["content"] for m in memories],
        )
    except Exception:
        logger.exception("AI request failed")
        raise HTTPException(
            status_code=502,
            detail="AI provider request failed. Check server logs.",
        )

    check = verify_result(answer)
    task_id = str(uuid.uuid4())

    from database import connect_db
    with connect_db() as db:
        db.execute(
            """
            INSERT INTO tasks (id, user_id, goal, status, result)
            VALUES (?, ?, ?, ?, ?)
            """,
            (task_id, user_id, body.prompt, "completed", answer),
        )

    return {
        "task_id": task_id,
        "answer": answer,
        "verification": check,
    }


@app.post("/api/memory")
def create_memory(
    body: MemoryRequest,
    user_id: str = Depends(require_auth),
):
    return {
        "id": save_memory(user_id, body.content),
        "status": "saved",
    }


@app.get("/api/memory")
def get_memories(
    q: str = "",
    user_id: str = Depends(require_auth),
):
    return {"items": search_memory(user_id, q)}


@app.delete("/api/memory/{memory_id}")
def remove_memory(
    memory_id: int,
    user_id: str = Depends(require_auth),
):
    if not delete_memory(user_id, memory_id):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted"}


@app.post("/api/feedback")
def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(require_auth),
):
    feedback_id = record_feedback(
        user_id,
        body.task,
        body.response,
        body.rating,
        body.notes,
    )
    return {"id": feedback_id, "status": "recorded"}


@app.get("/api/learning")
def learning_summary(user_id: str = Depends(require_auth)):
    return get_learning_summary(user_id)


@app.post("/api/improvements/propose")
def create_proposal(
    body: ProposalRequest,
    user_id: str = Depends(require_auth),
):
    try:
        return propose_change(
            user_id,
            body.filename,
            body.proposed_content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/improvements")
def get_proposals(user_id: str = Depends(require_auth)):
    return {"items": list_proposals(user_id)}
