"""Android dashboard additions and source-backed learning without a language model."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

import learning
import research
from main import app
from security import AuthenticatedUser


class WebLearningRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=10)


@app.post("/api/web-learning")
async def learn_from_web(
    body: WebLearningRequest,
    user_id: AuthenticatedUser,
) -> dict[str, Any]:
    """Search explicit user requests and queue excerpts for owner approval."""
    topic = body.topic.strip()
    if not topic:
        raise HTTPException(status_code=422, detail="Research topic cannot be empty.")
    try:
        sources = await research.search_web(topic, body.max_results)
    except research.ResearchConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except research.ResearchProviderError as exc:
        raise HTTPException(status_code=502, detail="Internet search is temporarily unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not sources:
        return {
            "topic": topic,
            "summary": "No useful search results were found.",
            "sources": [],
            "approval_status": None,
            "ai_model_used": False,
        }

    excerpts: list[str] = []
    source_urls: list[str] = []
    response_sources: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        title = str(source.get("title") or "Untitled source").strip()[:300]
        content = str(source.get("content") or "").strip()[:1500]
        url = str(source.get("url") or "").strip()[:2000]
        published_date = source.get("published_date")
        excerpts.append(f"[{index}] {title}\n{content}")
        source_urls.append(url)
        response_sources.append({
            "index": index,
            "title": title,
            "url": url,
            "content": content,
            "published_date": published_date,
        })

    summary = (
        "Web search excerpts (no generative AI was used). Verify claims at the sources:\n\n"
        + "\n\n".join(excerpts)
    )
    record_id = learning.save_learning_record(
        user_id=user_id,
        topic=topic[:200],
        summary=summary[:12000],
        source="\n".join(source_urls)[:1000],
    )
    return {
        "topic": topic,
        "summary": summary,
        "sources": response_sources,
        "learning_record_id": record_id,
        "approval_status": "pending",
        "ai_model_used": False,
    }
