"""
Thin repository layer over sqlite3. Keeps SQL out of the API routes.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from backend.database.db import get_db


def create_conversation(
    title: str = "New Chat",
    model: Optional[str] = None,
    provider: Optional[str] = None,
    project_id: Optional[int] = None,
    system_prompt: Optional[str] = None,
) -> dict[str, Any]:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO conversations (title, model, provider, project_id, system_prompt)
               VALUES (?, ?, ?, ?, ?)""",
            (title, model, provider, project_id, system_prompt),
        )
        conv_id = cur.lastrowid
        row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        return dict(row)


def get_conversation(conversation_id: int) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None


def list_conversations(project_id: Optional[int] = None, include_archived: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM conversations WHERE 1=1"
    params: list[Any] = []
    if project_id is not None:
        query += " AND project_id = ?"
        params.append(project_id)
    if not include_archived:
        query += " AND is_archived = 0"
    query += " ORDER BY updated_at DESC"
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def rename_conversation(conversation_id: int, title: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?",
            (title, conversation_id),
        )


def archive_conversation(conversation_id: int, archived: bool = True) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE conversations SET is_archived = ? WHERE id = ?",
            (1 if archived else 0, conversation_id),
        )


def delete_conversation(conversation_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    model: Optional[str] = None,
    tool_calls: Optional[list] = None,
    citations: Optional[list] = None,
) -> dict[str, Any]:
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO messages (conversation_id, role, content, model, tool_calls_json, citations_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                conversation_id,
                role,
                content,
                model,
                json.dumps(tool_calls) if tool_calls else None,
                json.dumps(citations) if citations else None,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?",
            (conversation_id,),
        )
        msg_id = cur.lastrowid
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
        return dict(row)


def get_messages(conversation_id: int) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def set_message_feedback(message_id: int, feedback: Optional[str]) -> None:
    with get_db() as conn:
        conn.execute("UPDATE messages SET feedback = ? WHERE id = ?", (feedback, message_id))
