from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    username: str
    avatar: str
    message: str


class MessageResponse(BaseModel):
    id: int
    username: str
    avatar: str
    message: str
    is_bot: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class TypingEvent(BaseModel):
    username: str
    avatar: str
    is_typing: bool
