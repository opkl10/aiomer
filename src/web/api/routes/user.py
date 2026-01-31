"""User routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...auth import get_current_user, get_password_hash, verify_password
from ...database import get_db
from ...models import Conversation, Message, TrainingEntry, User
from ...schemas import (
    ConversationResponse,
    PasswordChange,
    TrainingEntryResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name

    if update_data.email is not None:
        # Check if email is taken
        result = await db.execute(
            select(User).where(User.email == update_data.email, User.id != current_user.id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="כתובת האימייל כבר קיימת במערכת",
            )
        current_user.email = update_data.email

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change user password."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="הסיסמה הנוכחית שגויה",
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {"message": "הסיסמה שונתה בהצלחה"}


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations for current user."""
    # Query conversations with message count
    stmt = (
        select(
            Conversation,
            func.count(Message.id).label("message_count"),
        )
        .outerjoin(Message)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    conversations = []
    for conv, message_count in rows:
        conversations.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=message_count,
            )
        )

    return conversations


@router.get("/training-entries", response_model=list[TrainingEntryResponse])
async def get_user_training_entries(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all training entries for current user."""
    result = await db.execute(
        select(TrainingEntry)
        .where(TrainingEntry.user_id == current_user.id)
        .order_by(TrainingEntry.created_at.desc())
    )
    entries = result.scalars().all()

    return entries


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user statistics."""
    # Count conversations
    result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    conversation_count = result.scalar() or 0

    # Count messages
    result = await db.execute(
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.user_id == current_user.id)
    )
    message_count = result.scalar() or 0

    # Count training entries
    result = await db.execute(
        select(func.count(TrainingEntry.id)).where(TrainingEntry.user_id == current_user.id)
    )
    training_count = result.scalar() or 0

    return {
        "conversations": conversation_count,
        "messages": message_count,
        "training_entries": training_count,
    }
