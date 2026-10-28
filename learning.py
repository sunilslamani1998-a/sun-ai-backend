from __future__ import annotations

from collections import Counter
from typing import Any

import database

def record_feedback(
    user_id: str,
    message: str,
    rating: int,
    details: str | None = None,
) -> int:
    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("Feedback message cannot be empty.")
    if not 1 <= int(rating) <= 5:
        raise ValueError("Rating must be between 1 and 5.")

    cleaned_details = details.strip() if details is not None else None
    if cleaned_details == "":
        cleaned_details = None

    return database.add_feedback(
        user_id=user_id,
        message=cleaned_message,
        rating=int(rating),
        details=cleaned_details,
    )

def get_feedback_history(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return database.get_feedback(user_id=user_id, limit=limit)

def summarize_feedback(user_id: str, limit: int = 100) -> dict[str, Any]:
    feedback_items = get_feedback_history(user_id=user_id, limit=limit)
    if not feedback_items:
        return {
            "count": 0,
            "average_rating": None,
            "rating_distribution": {},
            "positive_count": 0,
            "negative_count": 0,
        }

    ratings = [int(item["rating"]) for item in feedback_items]
    distribution = Counter(ratings)

    return {
        "count": len(ratings),
        "average_rating": round(sum(ratings) / len(ratings), 2),
        "rating_distribution": {
            str(rating): distribution.get(rating, 0)
            for rating in range(1, 6)
        },
        "positive_count": sum(1 for rating in ratings if rating >= 4),
        "negative_count": sum(1 for rating in ratings if rating <= 2),
    }

def save_learning_record(
    user_id: str,
    topic: str,
    summary: str,
    source: str | None = None,
) -> int:
    cleaned_topic = topic.strip()
    cleaned_summary = summary.strip()

    if not cleaned_topic:
        raise ValueError("Learning topic cannot be empty.")
    if not cleaned_summary:
        raise ValueError("Learning summary cannot be empty.")
    if len(cleaned_topic) > 200:
        raise ValueError("Learning topic is too long.")
    if len(cleaned_summary) > 12000:
        raise ValueError("Learning summary is too long.")

    return database.add_learning_record(
        user_id=user_id,
        topic=cleaned_topic,
        summary=cleaned_summary,
        source=source,
    )

def get_learning_history(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return database.get_learning_records(user_id=user_id, limit=limit)

def build_learning_context(user_id: str, limit: int = 5) -> list[str]:
    records = get_learning_history(user_id=user_id, limit=limit)
    return [
        f"Topic: {record['topic']}\nSummary: {record['summary']}"
        for record in records
        if record.get("topic") and record.get("summary")
    ]
