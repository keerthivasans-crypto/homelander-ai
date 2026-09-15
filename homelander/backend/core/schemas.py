from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ChatSettings(BaseModel):
    temperature: float = 0.7
    web_search: bool = False
    deep_research: bool = False
    reasoning: bool = False
    max_tokens: Optional[int] = None


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    model: Optional[str] = None
    provider: str = "ollama"
    project_id: Optional[int] = None
    settings: ChatSettings = Field(default_factory=ChatSettings)


class MessageFeedbackRequest(BaseModel):
    feedback: Optional[str] = None  # "up" | "down" | None to clear


class ConversationCreateRequest(BaseModel):
    title: str = "New Chat"
    model: Optional[str] = None
    provider: str = "ollama"
    project_id: Optional[int] = None
    system_prompt: Optional[str] = None


class ConversationRenameRequest(BaseModel):
    title: str


class PullModelRequest(BaseModel):
    model: str
    provider: str = "ollama"
