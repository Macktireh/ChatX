from sqlalchemy import text
from sqlalchemy.orm import Session

from models.message import Message
from schemas.message import MessageCreate


class MessageService:
    @staticmethod
    def create_message(db: Session, message_data: MessageCreate, is_bot: bool = False) -> Message:
        """Crée un nouveau message et déclenche une notification PostgreSQL"""
        db_message = Message(
            username=message_data.username,
            avatar=message_data.avatar,
            message=message_data.message,
            is_bot=is_bot,
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)

        # Déclencher la notification PostgreSQL avec l'ID du message
        try:
            # Utiliser text() avec un paramètre bindé pour éviter l'injection SQL
            db.execute(
                text("SELECT pg_notify('chat', :message_id)"),
                {"message_id": str(db_message.id)}
            )
            db.commit()
        except Exception as e:
            print(f"Erreur lors de la notification PostgreSQL: {e}")

        return db_message

    @staticmethod
    def get_recent_messages(db: Session, limit: int = 50) -> list[Message]:
        """Récupère les messages récents"""
        messages = db.query(Message).order_by(Message.timestamp.desc()).limit(limit).all()
        return list(reversed(messages))  # Inverser pour avoir l'ordre chronologique

    @staticmethod
    def get_message_by_id(db: Session, message_id: int) -> Message:
        """Récupère un message par son ID"""
        return db.query(Message).filter(Message.id == message_id).first()
