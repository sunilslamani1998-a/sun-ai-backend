from __future__ import annotations

import re
from typing import Any

import database
from config import settings

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())

def tokenize(text: str) -> set[str]:
    normalized = normalize_text(text)
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_'-]+", normalized)
        if len(token) >= 2
    }

def save_memory(
    user_id: str,
    content: str,
    category: str = "general",
    importance: int = 1,
) -> int:
    cleaned_content = content.strip()
    cleaned_category = category.strip().lower() or "general"

    if not cleaned_content:
        raise ValueError("Memory content cannot be empty.")
    if len(cleaned_content) > settings.max_prompt_length:
        raise ValueError("Memory content is too long.")
    if len(cleaned_category) > 64:
        raise ValueError("Memory category is too long.")

    return database.add_memory(
        user_id=user_id,
        content=cleaned_content,
        category=cleaned_category,
        importance=max(1, min(5, int(importance))),
    )

def list_memories(user_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    effective_limit = (
        settings.max_memory_items
        if limit is None
        else max(1, min(500, int(limit)))
    )
    return database.get_memories(user_id=user_id, limit=effective_limit)

def search_memories(user_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    memories = database.get_memories(user_id=user_id, limit=500)
    scored: list[tuple[int, dict[str, Any]]] = []

    for memory in memories:
        content = str(memory.get("content", ""))
        memory_tokens = tokenize(content)
        overlap = query_tokens.intersection(memory_tokens)
        if not overlap:
            continue
        score = len(overlap) + max(0, int(memory.get("importance", 1)) - 1)
        scored.append((score, memory))

    scored.sort(key=lambda item: (item[0], item[1].get("created_at", "")), reverse=True)
    safe_limit = max(1, min(100, int(limit)))
    return [memory for _, memory in scored[:safe_limit]]

def delete_user_memory(user_id: str, memory_id: int) -> bool:
    return database.delete_memory(user_id=user_id, memory_id=memory_id)

def clear_user_memories(user_id: str) -> int:
    return database.clear_memories(user_id)

def build_memory_context(user_id: str, query: str, limit: int = 8) -> list[str]:
    relevant_memories = search_memories(user_id=user_id, query=query, limit=limit)
    return [
        str(memory["content"])
        for memory in relevant_memories
        if memory.get("content")
    ]
