from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from config.settings import get_settings
from models.message import Message
from schemas.message import MessageCreate
from services.message_service import MessageService


class BotService:
    BOT_AVATAR = "https://ollaix-ui.pages.dev/chatbot.png"
    BOT_USERNAME = "ChatBot"

    def should_respond(self, message: str) -> bool:
        return "@bot" in message.lower()

    def generate_response(
        self, message: str, username: str, conversation_context: list[Message]
    ) -> str:
        client = genai.Client(api_key=get_settings().gemini_api_key)

        system_prompt = """Tu es un assistant qui réponde aux demandes des utilisateurs. Si on te demande qui tu es, tu réponds que tu es un assistant qui réponde aux demandes des utilisateurs. Et tu répond en français à chaque fois.

Règles IMPORTANTES :
- Réponds UNIQUEMENT avec ton message
- Sois naturel et conversationnel
"""  # noqa: E501
        if conversation_context:
            context_text = "\n".join(
                [
                    f"{msg.username}: {msg.message}; is_bot: {msg.is_bot}"
                    for msg in conversation_context
                ]
            )
        else:
            context_text = "Début de la discussion"

        user_prompt = f"""Contexte de la conversation :
{context_text}

Génère maintenant TON message de réponse courte.
Réponds UNIQUEMENT avec le message, sans guillemets ni préambule.
Voici le demande de l'utilisateur :
Message Utilisateur: {message}; Nom Utilisateur: {username}"
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=user_prompt,
        )

        return response.text  # type: ignore

    def process_bot_response(
        self, db: Session, message: str, username: str, message_service: MessageService
    ) -> None:
        """Traite la réponse du bot en arrière-plan"""
        try:
            conversation_context = message_service.get_recent_messages(db)
            bot_response = self.generate_response(message, username, conversation_context)

            bot_message_data = MessageCreate(
                username=self.BOT_USERNAME, avatar=self.BOT_AVATAR, message=bot_response
            )

            message_service.create_message(db, bot_message_data, is_bot=True)
        except Exception as e:
            # Log l'erreur (ajoutez votre logger ici)
            print(f"Erreur lors de la génération de réponse bot: {e}")
