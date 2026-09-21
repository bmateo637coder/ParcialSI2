from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.assistant import ChatConversation, ChatMessage
from app.models.user import User
from app.schemas import (
    ChatConversationResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    RecommendationResponse,
)
from app.services.assistant import generate_answer
from app.services.recommendations import recommend

router = APIRouter()


# ======================================================================
# CU23 — CONSULTAR ASISTENTE VIRTUAL (CHATBOT)
# ======================================================================


def _conversation_response(conv: ChatConversation) -> ChatConversationResponse:
    return ChatConversationResponse(
        id=conv.id,
        created_at=conv.created_at,
        messages=[ChatMessageResponse(
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        ) for m in conv.messages],
    )


@router.post("/assistant/chat", response_model=ChatResponse,
             summary="Enviar mensaje al asistente virtual (CU23)")
def chat(payload: ChatRequest, user: User = Depends(get_current_user),
         db: Session = Depends(get_db)):
    conv = None
    if payload.conversation_id:
        conv = db.get(ChatConversation, payload.conversation_id)
        if conv is None or conv.client_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Conversación no encontrada")

    if conv is None:
        conv = ChatConversation(client_id=user.id)
        db.add(conv)
        db.flush()

    history = [{"role": m.role, "content": m.content} for m in conv.messages]
    db.add(ChatMessage(conversation_id=conv.id, role="user", content=payload.message))
    reply, suggestions = generate_answer(db, user, payload.message, history=history)
    db.add(ChatMessage(conversation_id=conv.id, role="assistant", content=reply))

    db.commit()
    return ChatResponse(conversation_id=conv.id, reply=reply, suggestions=suggestions)


@router.get("/assistant/conversations", response_model=list[ChatConversationResponse],
            summary="Listar mis conversaciones con el asistente (CU23)")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ChatConversation)
        .filter(ChatConversation.client_id == user.id)
        .order_by(ChatConversation.id.desc())
        .all()
    )
    return [_conversation_response(conv) for conv in rows]


@router.get("/assistant/conversations/{conversation_id}",
            response_model=ChatConversationResponse,
            summary="Consultar una conversación del asistente (CU23)")
def get_conversation(conversation_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    conv = db.get(ChatConversation, conversation_id)
    if conv is None or conv.client_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Conversación no encontrada")
    return _conversation_response(conv)


# ======================================================================
# CU22 — RECOMENDAR PRENDAS (IA)
# ======================================================================


@router.get("/recommendations", response_model=RecommendationResponse,
            summary="Prendas recomendadas para el cliente (CU22)")
def get_recommendations(limit: int = 8, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    return recommend(db, user.id, max(1, min(limit, 20)))