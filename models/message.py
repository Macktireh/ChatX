from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from config.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False)
    avatar = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_bot = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "avatar": self.avatar,
            "message": self.message,
            "is_bot": self.is_bot,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None # type: ignore
        }