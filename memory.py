from database import connect_db


def save_memory(user_id: str, content: str) -> int:
    content = content.strip()
    if not content or len(content) > 5000:
        raise ValueError("Memory must contain 1–5000 characters.")

    with connect_db() as db:
        cur = db.execute(
            "INSERT INTO memories (user_id, content) VALUES (?, ?)",
            (user_id, content),
        )
        return cur.lastrowid


def search_memory(user_id: str, query: str, limit: int = 10):
    words = [w for w in query.lower().split() if len(w) > 2][:8]

    with connect_db() as db:
        rows = db.execute(
            """
            SELECT id, content, created_at FROM memories
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 200
            """,
            (user_id,),
        ).fetchall()

    if not words:
        return [dict(r) for r in rows[:limit]]

    ranked = []
    for row in rows:
        score = sum(
            word in row["content"].lower() for word in words
        )
        if score:
            ranked.append((score, dict(row)))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked[:limit]]


def delete_memory(user_id: str, memory_id: int) -> bool:
    with connect_db() as db:
        cur = db.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        return cur.rowcount == 1
