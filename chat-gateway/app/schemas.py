from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """system_id/user_id는 JWT 사용 시 생략 가능(토큰에서 사용)."""
    system_id: str | None = Field(None, min_length=1, max_length=64)
    user_id: str | None = Field(None, min_length=1, max_length=256)
    message: str = Field(..., min_length=1)
    conversation_id: str | None = None
    inputs: dict | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str | None = None
    answer: str | None = None
    metadata: dict | None = None


class ConversationItem(BaseModel):
    id: str
    name: str | None = None
    created_at: int | None = None


class MessageItem(BaseModel):
    id: str
    role: str
    content: str | None = None
    created_at: int | None = None
