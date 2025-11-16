import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
from playwright.async_api import Browser, Page, async_playwright

from config.settings import BASE_DIR, get_settings


@dataclass
class AgentConfig:
    """Configuration d'un agent"""

    name: str
    gender: str
    specialist: str
    avatar: str
    role: str
    position: str


class ConversationAgent:
    """Agent simulant un utilisateur dans le chat"""

    def __init__(
        self,
        config: AgentConfig,
        gemini_api_key: str,
        base_url: str = "http://localhost:8000",
        headless: bool = True,
    ):
        self.config = config
        self.gemini_api_key = gemini_api_key
        self.base_url = base_url
        self.page: Page | None = None
        self.browser: Browser | None = None
        self.conversation_history: list[str] = []
        self.headless = headless

    async def initialize(self, playwright):
        """Initialiser le navigateur et la page"""
        self.browser = await playwright.chromium.launch(headless=self.headless)
        context = await self.browser.new_context()  # type: ignore
        self.page = await context.new_page()

    async def join_chat(self):
        """Rejoindre le chat avec les informations de l'agent"""
        if not self.page:
            raise ValueError("Page non initialisée")

        await self.page.context.add_cookies(
            [
                {"name": "username", "value": self.config.name, "url": self.base_url},
                {"name": "avatar", "value": self.config.avatar, "url": self.base_url},
            ]
        )

        # Attendre d'être sur la page de chat
        await self.page.goto(f"{self.base_url}/chat")
        await self.page.wait_for_load_state("domcontentloaded")

        print(f"✅ {self.config.name} a rejoint le chat")

    async def wait_for_messages(self, timeout: int = 2000):
        """Attendre de nouveaux messages"""
        await asyncio.sleep(timeout / 1000)

    async def get_last_messages(self, count: int = 10) -> list[dict[str, str]]:
        """Récupérer les derniers messages du chat"""
        if not self.page:
            return []

        try:
            # Attendre un court instant pour s'assurer que les messages sont chargés
            await self.page.wait_for_selector(".chat-bubble", timeout=2000)

            # # Récupérer les messages visibles
            # messages = await self.page.locator(".chat-bubble").all_text_contents()

            chat_elements = await self.page.locator(".chat").all()
            messages = []
            for chat in chat_elements:  # Ne prendre que les N derniers
                try:
                    # Extraire le username depuis .chat-header
                    username_element = chat.locator(".chat-header")
                    username_text = await username_element.text_content()

                    # Nettoyer le username (enlever le badge "Bot" et le timestamp)
                    username = username_text.split("\n")[1].strip() if username_text else "Unknown"

                    # Extraire le message depuis .chat-bubble
                    message_element = chat.locator(".chat-bubble")
                    message = await message_element.text_content()
                    message = message.strip() if message else ""

                    # Remplacer le username par "you" si c'est le message de l'agent actuel
                    display_username = "vous" if username == self.config.name else username

                    messages.append({"username": display_username, "message": message})
                except Exception as e:
                    print(f"⚠️ Erreur lors de l'extraction d'un message: {e}")
                    continue

            # Ne garder que les N derniers messages (sauf les siens)
            # return messages[-count:] if messages else []
            return messages
        except Exception:
            return []

    def generate_response(self, conversation_context: list[dict[str, str]], theme: str) -> str:
        """Générer une réponse avec Gemini"""
        client = genai.Client(api_key=self.gemini_api_key)

        system_prompt = f"""Tu es {self.config.name}, {self.config.specialist}.
Tu participes à une discussion et débat sur le thème : "{theme}".

Règles IMPORTANTES :
- Réponds UNIQUEMENT avec ton message
- Sois {self.config.role} selon ta position définie ci-dessus
- N'hésite PAS à contredire les autres si ça ne correspond pas à ta position
- Défends ta vision avec des arguments concrets
- Sois naturel et conversationnel
- Ne répète pas exactement ce qui a été dit
- Pas de formule de politesse excessive
- Reste dans le contexte de la conversation

STYLE DE COMMUNICATION selon ton rôle :
- Si optimiste : Enthousiaste, positif, voit les opportunités
- Si critique : Sceptique, soulève des problèmes, sentiment négatif, pose des questions difficiles
- Si pragmatique : Factuel, équilibré, cherche des solutions concrètes
- Si prudent : Mesuré, souligne les risques, demande des garanties
"""
        if conversation_context:
            context_text = "\n".join(
                [f"{msg['username']}: {msg['message']}" for msg in conversation_context]
            )
        else:
            context_text = f"Début de la discussion sur : {theme}"

        user_prompt = f"""Contexte de la conversation :
{context_text}

Génère maintenant TON message de réponse courte.
Réponds UNIQUEMENT avec le message, sans guillemets ni préambule."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(system_instruction=system_prompt),
            contents=user_prompt,
        )

        message = response.text.strip()  # type: ignore

        # Nettoyer le message
        message = message.replace('"', "").replace("'", "'")

        return message

    async def send_message(self, message: str):
        """Envoyer un message dans le chat"""
        if not self.page:
            raise ValueError("Page non initialisée")

        # Remplir le champ de message
        message_input = self.page.locator("#message-input")
        await message_input.fill(message)

        # Attendre un peu (simulation de frappe)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Envoyer
        await self.page.click('button[type="submit"]')

        # Attendre que le message soit envoyé
        await asyncio.sleep(0.5)

        # print(f"💬 {self.config.name}: {message}")

    async def close(self):
        """Fermer le navigateur"""
        if self.browser:
            await self.browser.close()


class ConversationOrchestrator:
    """Orchestrateur de la conversation entre agents"""

    def __init__(
        self,
        agents_file: Path | str,
        gemini_api_key: str,
        base_url: str = "http://localhost:8000",
        num_rounds: int = 10,
    ):
        self.agents_file = agents_file
        self.gemini_api_key = gemini_api_key
        self.base_url = base_url
        self.agents: list[ConversationAgent] = []
        self.theme: str = ""
        self.conversation_history: list[dict] = []
        self.num_rounds = num_rounds

    def load_agents_config(self) -> tuple[str, list[AgentConfig]]:
        """Charger la configuration des agents depuis le fichier JSON"""
        with open(self.agents_file, encoding="utf-8") as f:
            data = json.load(f)

        theme = data.get("theme_conversation", "")
        agents_data = data.get("agents", [])

        agents = []
        for i, agent_data in enumerate(agents_data):
            # Choisir un avatar en fonction du genre
            if agent_data["Gender"] == "M":
                avatar = f"https://avatar.iran.liara.run/public/boy?username={i + 1}"
            else:
                avatar = f"https://avatar.iran.liara.run/public/girl?username={i + 1}"

            agents.append(
                AgentConfig(
                    name=agent_data["Name"],
                    gender=agent_data["Gender"],
                    specialist=agent_data["Specialist"],
                    avatar=avatar,
                    role=agent_data.get("Role", "neutre"),
                    position=agent_data.get("Position", ""),
                )
            )

        return theme, agents

    async def initialize_agents(self):
        """Initialiser tous les agents"""
        self.theme, agents_config = self.load_agents_config()

        async with async_playwright() as playwright:
            print(f"🎭 Initialisation de {len(agents_config)} agents...")

            for config in agents_config:
                agent = ConversationAgent(config, self.gemini_api_key, self.base_url)
                await agent.initialize(playwright)
                await agent.join_chat()
                self.agents.append(agent)

                print(f"   👤 {config.name} ({config.role}) - {config.specialist}")

                # Attendre un peu entre chaque connexion
                await asyncio.sleep(2)

            print("\n✅ Tous les agents sont connectés et prêts à débattre !\n")

            # Lancer la conversation
            await self.run_conversation()

    async def run_conversation(self):
        """Lancer la conversation entre les agents"""
        print(f"\n🎬 Démarrage de la conversation sur : {self.theme}\n")

        try:
            for round_num in range(self.num_rounds):
                print(f"\n--- Tour {round_num + 1}/{self.num_rounds} ---")

                for agent in self.agents:
                    # Attendre un peu avant chaque message
                    await asyncio.sleep(random.uniform(3, 6))

                    # Récupérer le contexte de conversation
                    last_messages = await agent.get_last_messages(count=5)
                    # context = "\n".join([f"- {msg}" for msg in last_messages[-3:]])

                    # if not context:
                    #     context = f"Début de la discussion sur : {self.theme}"

                    # Générer et envoyer la réponse
                    response = agent.generate_response(last_messages, self.theme)
                    await agent.send_message(response)

                    # Enregistrer dans l'historique
                    self.conversation_history.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "agent": agent.config.name,
                            "message": response,
                        }
                    )

        except KeyboardInterrupt:
            print("\n⚠️ Interruption par l'utilisateur")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Nettoyer et fermer tous les agents"""
        print("\n🧹 Nettoyage...")
        for agent in self.agents:
            await agent.close()
        print("✅ Nettoyage terminé")

        # Sauvegarder l'historique
        # self.save_conversation_history()

    def save_conversation_history(self):
        """Sauvegarder l'historique de la conversation"""
        filename = f"conversation_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {"theme": self.theme, "messages": self.conversation_history},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"📝 Historique sauvegardé dans {filename}")


async def main():
    """Point d'entrée principal"""
    # Configuration
    AGENTS_FILE = BASE_DIR / "agents.json"
    GEMINI_API_KEY = get_settings().gemini_api_key  # À remplacer
    BASE_URL = "http://localhost:8000"
    NUM_ROUNDS = 5  # Nombre de tours de conversation

    # print(AGENTS_FILE, GEMINI_API_KEY)

    # Créer l'orchestrateur
    orchestrator = ConversationOrchestrator(
        agents_file=AGENTS_FILE,
        gemini_api_key=GEMINI_API_KEY,
        base_url=BASE_URL,
        num_rounds=NUM_ROUNDS,
    )

    # Lancer la conversation
    await orchestrator.initialize_agents()


if __name__ == "__main__":
    asyncio.run(main())
