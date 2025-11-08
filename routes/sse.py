import asyncio
import json
from collections.abc import AsyncGenerator

import psycopg
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from config.settings import get_settings
from services.message_service import MessageService

router = APIRouter()
settings = get_settings()


def strip_psycopg_dialect(url: str) -> str:
    if "+psycopg" in url:
        return url.replace("+psycopg", "")
    return url


async def message_stream(last_event_id: str | None = None) -> AsyncGenerator:
    """Stream de messages via SSE avec PostgreSQL NOTIFY/LISTEN (psycopg v3)"""

    # Parser la DB URL pour psycopg v3
    db_url = strip_psycopg_dialect(settings.database_url)

    # Connexion PostgreSQL asynchrone pour LISTEN
    aconn = await psycopg.AsyncConnection.connect(conninfo=db_url, autocommit=True)
    channel_chat = "chat"
    channel_typing_event = "typing_event"

    try:
        # S'abonner au canal de notification
        async with aconn.cursor() as cursor:
            await cursor.execute(f"LISTEN {channel_chat};")
            await cursor.execute(f"LISTEN {channel_typing_event};")

        print(f"✅ Abonné aux canaux '{channel_chat}' et '{channel_typing_event}'")

        # Si last_event_id est fourni, envoyer les messages manqués
        if last_event_id:
            try:
                from config.database import SessionLocal
                from models.message import Message

                db = SessionLocal()
                missed_messages = db.query(Message).filter(Message.id > int(last_event_id)).all()

                for msg in missed_messages:
                    yield {
                        "id": str(msg.id),
                        "event": "message",
                        "data": json.dumps(msg.to_dict()),
                    }
                db.close()
            except (ValueError, Exception) as e:
                print(f"⚠️ Erreur lors de la récupération des messages manqués: {e}")

        # Boucle d'écoute des notifications avec psycopg v3
        gen = aconn.notifies()
        async for notify in gen:
            try:
                # Le payload contient l'ID du message
                if notify.channel == channel_chat:
                    message_id = int(notify.payload)

                    print(f"📨 Notification reçue pour le message ID: {message_id}")

                    # Récupérer le message depuis la DB
                    from config.database import SessionLocal

                    db = SessionLocal()
                    message = MessageService.get_message_by_id(db, message_id)
                    db.close()

                    if message:
                        yield {
                            "id": str(message.id),
                            "event": "message",
                            "data": json.dumps(message.to_dict()),
                        }
                elif notify.channel == channel_typing_event:
                    # Le payload contient les données de typing en JSON
                    typing_data = json.loads(notify.payload)

                    print(f"✍️ Notification typing reçue: {typing_data}")

                    yield {"event": "typing", "data": json.dumps(typing_data)}
            except Exception as e:
                print(f"❌ Erreur lors du traitement de la notification: {e}")
                continue

    except asyncio.CancelledError:
        print("🔌 Connexion SSE fermée par le client")
        raise
    except Exception as e:
        print(f"❌ Erreur dans le stream SSE: {e}")
        raise
    finally:
        await aconn.close()
        print("🔒 Connexion PostgreSQL fermée")


@router.get("/api/stream")
async def stream_messages(request: Request):
    """Endpoint SSE pour les messages en temps réel"""
    # Récupérer le dernier ID d'événement si présent
    last_event_id = request.headers.get("Last-Event-ID")

    print(f"🌐 Nouvelle connexion SSE (Last-Event-ID: {last_event_id})")

    return EventSourceResponse(
        message_stream(last_event_id),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
