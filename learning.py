from database import connect_db


def record_feedback(
    user_id: str,
    task: str,
    response: str,
    rating: int,
    notes: str = "",
):
    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5.")

    with connect_db() as db:
        cur = db.execute(
            """
            INSERT INTO feedback
                (user_id, task, response, rating, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                task[:2000],
                response[:20000],
                rating,
                notes[:2000],
            ),
        )
        return cur.lastrowid


def get_learning_summary(user_id: str):
    with connect_db() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS total,
                   AVG(rating) AS average_rating
            FROM feedback WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        recent = db.execute(
            """
            SELECT task, rating, notes, created_at
            FROM feedback WHERE user_id = ?
            ORDER BY id DESC LIMIT 10
            """,
            (user_id,),
        ).fetchall()

    return {
        "feedback_count": row["total"],
        "average_rating": (
            round(row["average_rating"], 2)
            if row["average_rating"] is not None else None
        ),
        "recent_feedback": [dict(r) for r in recent],
    }
