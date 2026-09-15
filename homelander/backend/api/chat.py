from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core.schemas import ChatRequest, MessageFeedbackRequest
from backend.database import repository as repo
from backend.models.base_provider import ChatMessage, ProviderError
from backend.models.registry import registry

router = APIRouter(prefix="/api/chat", tags=["chat"])

DEFAULT_SYSTEM_PROMPT = (
    "You are HOMELANDER, a private, local-first AI assistant. "
    "Be direct, accurate, and helpful. If you are unsure of something, say so "
    "rather than guessing."
)


@router.post("")
async def chat(req: ChatRequest):
    """
    Send a message and stream back HOMELANDER's response as Server-Sent Events.

    Event types sent to the client:
      {"type": "user_message", "message": {...}}
      {"type": "token", "text": "..."}
      {"type": "done", "message": {...}}
      {"type": "error", "message": "..."}
    """
    # 1. Resolve or create the conversation.
    if req.conversation_id:
        conversation = repo.get_conversation(req.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        title = (req.message[:60] + "…") if len(req.message) > 60 else req.message
        conversation = repo.create_conversation(
            title=title or "New Chat",
            model=req.model,
            provider=req.provider,
            project_id=req.project_id,
        )

    model_name = req.model or conversation.get("model")
    if not model_name:
        raise HTTPException(
            status_code=400,
            detail="No model selected. Choose an installed model first.",
        )

    try:
        provider = registry.get(req.provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # 2. Persist the user's message immediately.
    user_msg = repo.add_message(conversation["id"], "user", req.message)

    # 3. Build the message list: system prompt + history + new message.
    history = repo.get_messages(conversation["id"])
    system_prompt = conversation.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    chat_messages = [ChatMessage(role="system", content=system_prompt)]
    for m in history:
        if m["role"] in ("user", "assistant"):
            chat_messages.append(ChatMessage(role=m["role"], content=m["content"]))

    async def event_stream():
        yield f"data: {json.dumps({'type': 'user_message', 'message': user_msg, 'conversation_id': conversation['id']})}\n\n"

        full_text = ""
        try:
            status = await provider.health_check()
            if status.value != "online":
                raise ProviderError(
                    "HOMELANDER cannot connect to the local AI engine. "
                    "Please start Ollama and try again."
                )
            async for chunk in provider.generate(
                model=model_name,
                messages=chat_messages,
                temperature=req.settings.temperature,
                max_tokens=req.settings.max_tokens,
            ):
                if chunk.text:
                    full_text += chunk.text
                    yield f"data: {json.dumps({'type': 'token', 'text': chunk.text})}\n\n"
                if chunk.done:
                    break
        except ProviderError as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': exc.user_message})}\n\n"
            if full_text:
                repo.add_message(conversation["id"], "assistant", full_text, model=model_name)
            return

        assistant_msg = repo.add_message(
            conversation["id"], "assistant", full_text, model=model_name
        )
        yield f"data: {json.dumps({'type': 'done', 'message': assistant_msg})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
async def list_conversations(project_id: int | None = None):
    return {"conversations": repo.list_conversations(project_id=project_id)}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    conversation = repo.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation["messages"] = repo.get_messages(conversation_id)
    return conversation


@router.patch("/conversations/{conversation_id}/rename")
async def rename_conversation(conversation_id: int, title: str):
    repo.rename_conversation(conversation_id, title)
    return {"ok": True}


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(conversation_id: int):
    repo.archive_conversation(conversation_id, True)
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    repo.delete_conversation(conversation_id)
    return {"ok": True}


@router.patch("/messages/{message_id}/feedback")
async def message_feedback(message_id: int, req: MessageFeedbackRequest):
    repo.set_message_feedback(message_id, req.feedback)
    return {"ok": True}
