
from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
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
    connect_live_session,
)
from config import settings
from security import AuthenticatedUser
from verification import verify_response


# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Gemini Live ticket management
# -------------------------------------------------------------------

LIVE_TICKET_TTL_SECONDS = 60

# In-memory ticket storage.
# This works for a single application worker.
# Use Redis with atomic consume operations for multiple workers.
_live_tickets: dict[str, tuple[str, float]] = {}


def _clean_expired_live_tickets() -> None:
    now = time.monotonic()

    expired = [
        ticket
        for ticket, (_, expiry) in _live_tickets.items()
        if expiry <= now
    ]

    for ticket in expired:
        _live_tickets.pop(ticket, None)


def _create_live_ticket(user_id: str) -> str:
    _clean_expired_live_tickets()

    ticket = secrets.token_urlsafe(32)

    _live_tickets[ticket] = (
        str(user_id),
        time.monotonic() + LIVE_TICKET_TTL_SECONDS,
    )

    return ticket


def _consume_live_ticket(ticket: str) -> str | None:
    _clean_expired_live_tickets()

    entry = _live_tickets.pop(ticket, None)

    if entry is None:
        return None

    user_id, expiry = entry

    if expiry <= time.monotonic():
        return None

    return user_id


# -------------------------------------------------------------------
# Application lifecycle
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""

    logger.info("Starting SUN.AI application")

    try:
        database.init_db()
        logger.info("Database initialized successfully")

    except Exception:
        logger.exception("Database initialization failed")
        raise

    yield

    _live_tickets.clear()
    logger.info("SUN.AI application shutting down")


app = FastAPI(
    title=settings.app_name,
    description="SUN.AI Advanced personal AI assistant backend",
    version="0.1.0",
    lifespan=lifespan,
)


# -------------------------------------------------------------------
# CORS
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

    try:
        database_ok = database.check_database()

    except Exception:
        logger.exception("Database health check failed")
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "database": (
            "connected" if database_ok else "unavailable"
        ),
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
    """Send a prompt to Gemini with memory and learning context."""

    cleaned_prompt = body.prompt.strip()

    if not cleaned_prompt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Prompt cannot be empty.",
        )

    try:
        memory_context = memory.build_memory_context(
            user_id=user_id,
            query=cleaned_prompt,
            limit=8,
        )

        learning_context = learning.build_learning_context(
            user_id=user_id,
            limit=5,
        )

        response = await ask_ai(
            prompt=cleaned_prompt,
            memories=memory_context,
            learning_context=learning_context,
        )

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

    except AgentConfigurationError as exc:
        logger.exception("SUN.AI agent configuration error")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except AgentRequestError as exc:
        logger.exception("SUN.AI Gemini request failed")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        logger.warning("Invalid chat request: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Unexpected SUN.AI chat error")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected chat processing error occurred.",
        ) from exc


# -------------------------------------------------------------------
# Gemini Live - authenticated ticket creation
# -------------------------------------------------------------------

@app.post("/api/live/ticket")
async def create_live_ticket(
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """
    Create a short-lived, single-use Live WebSocket ticket.

    This endpoint uses the existing SUN.AI bearer authentication.
    The browser must not put its long-lived API token in the
    WebSocket URL.
    """

    api_key = settings.gemini_api_key.get_secret_value().strip()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured.",
        )

    if not settings.gemini_live_model.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_LIVE_MODEL is not configured.",
        )

    ticket = _create_live_ticket(str(user_id))

    return {
        "success": True,
        "ticket": ticket,
        "expires_in": LIVE_TICKET_TTL_SECONDS,
        "websocket_path": "/ws/live",
        "audio_input": "audio/pcm;rate=16000",
        "audio_output": "audio/pcm;rate=24000",
    }


# -------------------------------------------------------------------
# Gemini Live - WebSocket endpoint
# -------------------------------------------------------------------

@app.websocket("/ws/live")
async def gemini_live_websocket(
    websocket: WebSocket,
    ticket: str = Query(
        min_length=20,
        max_length=200,
    ),
):
    """
    Start an authenticated Gemini Live voice session.

    Browser -> server audio:
        {
            "type": "audio",
            "data": "BASE64_PCM_AUDIO"
        }

    Browser -> server text:
        {
            "type": "text",
            "text": "Hello Bittu"
        }

    Server -> browser audio:
        {
            "type": "audio",
            "data": "BASE64_PCM_AUDIO",
            "mime_type": "audio/pcm;rate=24000"
        }
    """

    user_id = _consume_live_ticket(ticket)

    if user_id is None:
        await websocket.close(
            code=1008,
            reason="Invalid or expired session ticket.",
        )
        return

    await websocket.accept()

    try:
        await _run_gemini_live_session(
            websocket=websocket,
            user_id=user_id,
        )

    except WebSocketDisconnect:
        logger.info("Live WebSocket disconnected.")

    except AgentConfigurationError:
        logger.exception("Gemini Live configuration error.")

        await _send_live_error(
            websocket,
            "Gemini Live is not configured correctly.",
        )

    except AgentRequestError:
        logger.exception("Gemini Live request failed.")

        await _send_live_error(
            websocket,
            "Gemini Live connection failed.",
        )

    except Exception:
        logger.exception("Unexpected Gemini Live WebSocket error.")

        await _send_live_error(
            websocket,
            "The live voice session encountered an error.",
        )

    finally:
        try:
            await websocket.close()
        except Exception:
            pass


async def _send_live_error(
    websocket: WebSocket,
    message: str,
) -> None:
    """Send a safe error message if the socket is still connected."""

    try:
        await websocket.send_json({
            "type": "error",
            "message": message,
        })
    except Exception:
        logger.debug(
            "Could not send WebSocket error message.",
            exc_info=True,
        )


# -------------------------------------------------------------------
# Gemini Live - session bridge
# -------------------------------------------------------------------

async def _run_gemini_live_session(
    websocket: WebSocket,
    user_id: str,
) -> None:
    """Bridge browser audio/text and Bittu's Gemini Live session."""

    try:
        from google.genai import types
    except ImportError as exc:
        logger.exception("Google GenAI SDK is unavailable.")

        raise AgentConfigurationError(
            "The google-genai package is not installed."
        ) from exc

    try:
        memory_context = memory.build_memory_context(
            user_id=user_id,
            query="Real-time voice conversation with Bittu",
            limit=8,
        )

        learning_context = learning.build_learning_context(
            user_id=user_id,
            limit=5,
        )

    except Exception:
        logger.exception("Could not load Live session context.")

        memory_context = []
        learning_context = []

    async with connect_live_session(
        language="english",
        memories=memory_context,
        learning_context=learning_context,
    ) as session:

        await websocket.send_json({
            "type": "connected",
            "assistant": "Bittu",
            "model": settings.gemini_live_model,
            "voice": settings.gemini_live_voice,
            "audio_input": "audio/pcm;rate=16000",
            "audio_output": "audio/pcm;rate=24000",
        })

        async def send_browser_audio() -> None:
            """Forward browser audio and text messages to Gemini."""

            while True:
                message = await websocket.receive_json()

                if not isinstance(message, dict):
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid WebSocket message.",
                    })
                    continue

                message_type = message.get("type")

                if message_type == "audio":
                    encoded_audio = message.get("data")

                    if not isinstance(encoded_audio, str):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Audio data must be base64 text.",
                        })
                        continue

                    try:
                        audio_bytes = base64.b64decode(
                            encoded_audio,
                            validate=True,
                        )
                    except (binascii.Error, ValueError):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid base64 audio data.",
                        })
                        continue

                    if (
                        not audio_bytes
                        or len(audio_bytes) > 256_000
                        or len(audio_bytes) % 2 != 0
                    ):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Audio chunk is invalid or too large.",
                        })
                        continue

                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=audio_bytes,
                            mime_type="audio/pcm;rate=16000",
                        )
                    )

                elif message_type == "text":
                    text_message = message.get("text")

                    if not isinstance(text_message, str):
                        continue

                    text_message = text_message.strip()

                    if not text_message:
                        continue

                    if len(text_message) > 12000:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Text message is too long.",
                        })
                        continue

                    await session.send_realtime_input(
                        text=text_message,
                    )

                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                    })

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Unsupported message type.",
                    })

        async def receive_gemini_audio() -> None:
            """Forward Gemini audio and transcription to the browser."""

            async for response in session.receive():
                server_content = getattr(
                    response,
                    "server_content",
                    None,
                )

                if server_content is None:
                    continue

                input_transcription = getattr(
                    server_content,
                    "input_transcription",
                    None,
                )

                if input_transcription is not None:
                    input_text = getattr(
                        input_transcription,
                        "text",
                        None,
                    )

                    if input_text:
                        await websocket.send_json({
                            "type": "input_transcription",
                            "text": input_text,
                        })

                output_transcription = getattr(
                    server_content,
                    "output_transcription",
                    None,
                )

                if output_transcription is not None:
                    output_text = getattr(
                        output_transcription,
                        "text",
                        None,
                    )

                    if output_text:
                        await websocket.send_json({
                            "type": "output_transcription",
                            "text": output_text,
                        })

                model_turn = getattr(
                    server_content,
                    "model_turn",
                    None,
                )

                if model_turn is not None:
                    for part in (
                        getattr(model_turn, "parts", None) or []
                    ):
                        inline_data = getattr(
                            part,
                            "inline_data",
                            None,
                        )

                        if inline_data is None:
                            continue

                        audio_data = getattr(
                            inline_data,
                            "data",
                            None,
                        )

                        mime_type = getattr(
                            inline_data,
                            "mime_type",
                            "audio/pcm;rate=24000",
                        )

                        if isinstance(audio_data, bytes):
                            encoded_audio = base64.b64encode(
                                audio_data
                            ).decode("ascii")

                        elif isinstance(audio_data, str):
                            encoded_audio = audio_data

                        else:
                            continue

                        await websocket.send_json({
                            "type": "audio",
                            "data": encoded_audio,
                            "mime_type": mime_type,
                        })

                if getattr(server_content, "interrupted", False):
                    await websocket.send_json({
                        "type": "interrupted",
                    })

                if getattr(server_content, "turn_complete", False):
                    await websocket.send_json({
                        "type": "turn_complete",
                    })

        browser_task = asyncio.create_task(
            send_browser_audio()
        )

        gemini_task = asyncio.create_task(
            receive_gemini_audio()
        )

        tasks = {
            browser_task,
            gemini_task,
        }

        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                exception = task.exception()

                if exception is not None:
                    raise exception

        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )


# -------------------------------------------------------------------
# Memory
# -------------------------------------------------------------------

@app.post("/api/memory")
async def create_memory(
    body: MemoryCreateRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:

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

    items = learning.get_feedback_history(
        user_id=user_id,
        limit=limit,
    )

    return {
        "count": len(items),
        "feedback": items,
    }


# -------------------------------------------------------------------
# Learning
# -------------------------------------------------------------------

@app.get("/api/learning")
async def learning_summary(
    user_id: AuthenticatedUser,
) -> dict[str, Any]:

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
