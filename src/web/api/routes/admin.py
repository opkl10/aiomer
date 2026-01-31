"""Admin routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....knowledge import KnowledgeBase
from ...auth import get_current_admin
from ...config import get_settings
from ...database import get_db
from ...models import Conversation, Message, TrainingEntry, User, UserRole
from ...schemas import SystemStats, UserAdminUpdate, UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def get_knowledge_base() -> KnowledgeBase:
    """Get knowledge base instance."""
    return KnowledgeBase(data_dir=str(settings.data_dir))


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide statistics."""
    # Total users
    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar() or 0

    # Active users
    result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = result.scalar() or 0

    # Total conversations
    result = await db.execute(select(func.count(Conversation.id)))
    total_conversations = result.scalar() or 0

    # Total messages
    result = await db.execute(select(func.count(Message.id)))
    total_messages = result.scalar() or 0

    # Total training entries
    result = await db.execute(select(func.count(TrainingEntry.id)))
    total_training_entries = result.scalar() or 0

    # Knowledge base size
    kb = get_knowledge_base()
    knowledge_base_size = kb.count()

    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        total_conversations=total_conversations,
        total_messages=total_messages,
        total_training_entries=total_training_entries,
        knowledge_base_size=knowledge_base_size,
    )


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="המשתמש לא נמצא",
        )

    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserAdminUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="המשתמש לא נמצא",
        )

    # Prevent admin from demoting themselves
    if user.id == current_user.id and update_data.role == UserRole.USER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="לא ניתן להסיר הרשאות מנהל מעצמך",
        )

    if update_data.role is not None:
        user.role = update_data.role

    if update_data.is_active is not None:
        # Prevent admin from deactivating themselves
        if user.id == current_user.id and not update_data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="לא ניתן להשבית את החשבון שלך",
            )
        user.is_active = update_data.is_active

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="לא ניתן למחוק את החשבון שלך",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="המשתמש לא נמצא",
        )

    await db.delete(user)
    await db.commit()

    return {"message": "המשתמש נמחק בהצלחה"}


@router.get("/training-entries")
async def get_all_training_entries(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all training entries."""
    result = await db.execute(
        select(TrainingEntry, User.username)
        .join(User)
        .order_by(TrainingEntry.created_at.desc())
    )
    rows = result.all()

    return [
        {
            "id": entry.id,
            "content": entry.content,
            "entry_type": entry.entry_type,
            "created_at": entry.created_at.isoformat(),
            "username": username,
        }
        for entry, username in rows
    ]


@router.delete("/training-entries/{entry_id}")
async def delete_training_entry(
    entry_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a training entry."""
    result = await db.execute(select(TrainingEntry).where(TrainingEntry.id == entry_id))
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="הרשומה לא נמצאה",
        )

    # Also delete from knowledge base if possible
    if entry.knowledge_id:
        kb = get_knowledge_base()
        kb.delete(entry.knowledge_id)

    await db.delete(entry)
    await db.commit()

    return {"message": "הרשומה נמחקה בהצלחה"}


@router.post("/knowledge/clear")
async def clear_knowledge_base(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Clear all knowledge from the knowledge base."""
    kb = get_knowledge_base()
    kb.clear()

    # Also clear training entries table
    await db.execute(delete(TrainingEntry))
    await db.commit()

    return {"message": "מאגר הידע נוקה בהצלחה"}
