"""Chat routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....conversation import ConversationEngine
from ....knowledge import KnowledgeBase
from ...auth import get_current_user
from ...config import get_settings
from ...database import get_db
from ...models import Conversation, Message, TrainingEntry, User
from ...schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationDetail,
    MessageResponse,
    TrainRequest,
    TrainResponse,
)

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()

# Shared knowledge base and conversation engine
_knowledge_base = None
_conversation_engine = None


def get_knowledge_base() -> KnowledgeBase:
    """Get shared knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase(data_dir=str(settings.data_dir))
    return _knowledge_base


def get_conversation_engine() -> ConversationEngine:
    """Get shared conversation engine instance."""
    global _conversation_engine
    if _conversation_engine is None:
        _conversation_engine = ConversationEngine(get_knowledge_base())
    return _conversation_engine


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response."""
    engine = get_conversation_engine()

    # Get or create conversation
    if request.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="השיחה לא נמצאה",
            )
    else:
        # Create new conversation
        # Generate title from first message
        title = request.message[:50] + "..." if len(request.message) > 50 else request.message
        conversation = Conversation(user_id=current_user.id, title=title)
        db.add(conversation)
        await db.flush()

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # Get AI response
    response_text = engine.process_input(request.message)

    # Save AI response
    ai_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
    )
    db.add(ai_message)

    await db.commit()
    await db.refresh(ai_message)

    return ChatResponse(
        response=response_text,
        conversation_id=conversation.id,
        message_id=ai_message.id,
    )


@router.post("/conversations", response_model=ConversationDetail)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation."""
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title or "שיחה חדשה",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[],
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="השיחה לא נמצאה",
        )

    # Sort messages by created_at
    messages = sorted(conversation.messages, key=lambda m: m.created_at)

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="השיחה לא נמצאה",
        )

    await db.delete(conversation)
    await db.commit()

    return {"message": "השיחה נמחקה בהצלחה"}


@router.post("/train", response_model=TrainResponse)
async def train_ai(
    request: TrainRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Train the AI with new knowledge."""
    engine = get_conversation_engine()

    # Process training
    result = engine.trainer.train_interactive(request.content)

    # Save training entry
    entry = TrainingEntry(
        user_id=current_user.id,
        content=request.content,
        entry_type=request.entry_type,
        knowledge_id=result.get("doc_id"),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return TrainResponse(
        success=result.get("status") == "success",
        message=result.get("message", ""),
        entry_id=entry.id,
    )


@router.get("/search")
async def search_knowledge(
    q: str,
    current_user: User = Depends(get_current_user),
):
    """Search the knowledge base."""
    kb = get_knowledge_base()
    results = kb.search(q, n_results=10)

    return {
        "query": q,
        "results": [
            {
                "content": r["content"],
                "score": round(r["score"] * 100),
                "metadata": r.get("metadata", {}),
            }
            for r in results
        ],
    }


@router.get("/stats")
async def get_knowledge_stats(
    current_user: User = Depends(get_current_user),
):
    """Get knowledge base statistics."""
    engine = get_conversation_engine()
    stats = engine.trainer.get_training_stats()

    return stats
