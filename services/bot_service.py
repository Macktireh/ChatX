import random
import re


class BotService:
    BOT_AVATAR = "https://ollaix-ui.pages.dev/chatbot.png"
    BOT_USERNAME = "ChatBot"

    RESPONSES = {
        "salut|bonjour|hello|hey": [
            "👋 Salut {user} ! Comment puis-je t'aider ?",
            "Hello {user} ! Ravi de te voir ici !",
            "Bonjour {user} ! Que puis-je faire pour toi ?",
        ],
        "comment ça va|ça va": [
            "Je vais très bien merci ! Et toi {user} ?",
            "Parfaitement bien ! Je suis là pour t'aider 😊",
        ],
        "aide|help": [
            "Je peux répondre à tes questions ! Mentionne-moi avec @bot suivi de ton message.",
            "Voici ce que je peux faire : répondre à tes salutations, te donner l'heure, et discuter avec toi !",
        ],
        "heure|quelle heure": [
            "Je ne peux pas voir l'heure exacte, mais tu peux la voir dans tes messages ! 🕐"
        ],
        "merci|thank": ["De rien {user} ! C'est un plaisir d'aider ! 😊", "Avec plaisir {user} !"],
        "au revoir|bye|ciao": [
            "Au revoir {user} ! À bientôt ! 👋",
            "Bye {user} ! Reviens quand tu veux !",
        ],
    }

    DEFAULT_RESPONSES = [
        "Hmm, je ne suis pas sûr de comprendre {user}. Peux-tu reformuler ?",
        "Intéressant {user} ! Peux-tu m'en dire plus ?",
        "Je suis encore en apprentissage {user}. Essaie de me demander autre chose !",
        "Désolé {user}, je n'ai pas de réponse à ça pour le moment 🤔",
    ]

    @classmethod
    def should_respond(cls, message: str) -> bool:
        return "@bot" in message.lower()

    @classmethod
    def generate_response(cls, message: str, username: str) -> str:
        clean_message = message.lower().replace("@bot", "").strip()

        for pattern, responses in cls.RESPONSES.items():
            if re.search(pattern, clean_message):
                response = random.choice(responses)
                return response.format(user=username)

        return random.choice(cls.DEFAULT_RESPONSES).format(user=username)
