from __future__ import annotations
from collections import Counter
from typing import Any
import database
from multilingual import normalize_language


def record_feedback(user_id: str, message: str, rating: int, details: str | None = None) -> int:
    message = message.strip()
    if not message:
        raise ValueError("Feedback message cannot be empty.")
    if not 1 <= int(rating) <= 5:
        raise ValueError("Rating must be between 1 and 5.")
    details = details.strip() if details is not None else None
    return database.add_feedback(user_id, message, int(rating), details or None)


def get_feedback_history(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return database.get_feedback(user_id, limit)


def summarize_feedback(user_id: str, limit: int = 100) -> dict[str, Any]:
    items = get_feedback_history(user_id, limit)
    if not items:
        return {"count": 0, "average_rating": None, "rating_distribution": {}, "positive_count": 0, "negative_count": 0}
    ratings = [int(item["rating"]) for item in items]
    distribution = Counter(ratings)
    return {"count": len(ratings), "average_rating": round(sum(ratings) / len(ratings), 2),
            "rating_distribution": {str(r): distribution.get(r, 0) for r in range(1, 6)},
            "positive_count": sum(r >= 4 for r in ratings), "negative_count": sum(r <= 2 for r in ratings)}


def save_learning_record(user_id: str, topic: str, summary: str, source: str | None = None, language: str = "english") -> int:
    topic, summary = topic.strip(), summary.strip()
    if not topic:
        raise ValueError("Learning topic cannot be empty.")
    if not summary:
        raise ValueError("Learning summary cannot be empty.")
    if len(topic) > 200:
        raise ValueError("Learning topic is too long.")
    if len(summary) > 12000:
        raise ValueError("Learning summary is too long.")
    source = source.strip() if source else None
    return database.add_learning_record(user_id, topic, summary, source or None, normalize_language(language))


def get_learning_history(user_id: str, limit: int = 100, approval_status: str | None = None) -> list[dict[str, Any]]:
    return database.get_learning_records(user_id, limit, approval_status)


def review_learning_record(user_id: str, record_id: int, approval_status: str) -> bool:
    return database.update_learning_approval(user_id, record_id, approval_status)


def build_learning_context(user_id: str, limit: int = 5) -> list[str]:
    approved = get_learning_history(user_id, limit, approval_status="approved")
    return [f"Topic: {r['topic']}\nSummary: {r['summary']}" for r in approved if r.get("topic") and r.get("summary")]
