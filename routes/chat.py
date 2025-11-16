import json

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.constants import AVATARS
from config.database import get_db
from schemas.message import MessageCreate, TypingEvent
from services.bot_service import BotService
from services.message_service import MessageService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil"""
    return templates.TemplateResponse("index.html", {"request": request, "avatars": AVATARS})


@router.post("/join")
async def join_chat(username: str = Form(...), avatar: str = Form(...)):
    """Rejoindre le chat"""
    response = RedirectResponse(url="/chat", status_code=303)
    response.set_cookie("username", username)
    response.set_cookie("avatar", avatar)
    return response


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):  # noqa: B008
    """Page de chat"""
    username = request.cookies.get("username")
    avatar = request.cookies.get("avatar")

    if not username or not avatar:
        return RedirectResponse(url="/")

    messages = MessageService.get_recent_messages(db)

    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "username": username, "avatar": avatar, "messages": messages},
    )


@router.post("/api/messages")
async def send_message(
    message_data: MessageCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)  # noqa: B008
):
    """Envoyer un message et déclencher une réponse bot en arrière-plan"""
    # Créer le message utilisateur immédiatement
    user_message = MessageService.create_message(db, message_data)

    bot_service = BotService()

    # Vérifier si le bot doit répondre
    if bot_service.should_respond(message_data.message):
        # Ajouter la génération de réponse en tâche d'arrière-plan
        background_tasks.add_task(
            bot_service.process_bot_response,
            db=db,
            message=message_data.message,
            username=message_data.username,
            message_service=MessageService,
        )

    # Retourner immédiatement la réponse sans attendre le bot
    return {"status": "success", "message": user_message.to_dict()}


@router.post("/api/typing")
async def send_typing(typing_event: TypingEvent, db: Session = Depends(get_db)) -> dict[str, str]:  # noqa: B008
    """Envoyer un événement typing"""
    try:
        typing_data = json.dumps(
            {
                "username": typing_event.username,
                "avatar": typing_event.avatar,
                "is_typing": typing_event.is_typing,
            }
        )

        # Envoyer la notification via PostgreSQL
        db.execute(text("SELECT pg_notify('typing_event', :data)"), {"data": typing_data})
        db.commit()

        return {"status": "success"}
    except Exception as e:
        print(f"❌ Erreur typing: {e}")
        return {"status": "error", "message": str(e)}
