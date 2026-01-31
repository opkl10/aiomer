"""Pydantic schemas for API validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# === Auth Schemas ===


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(min_length=6)


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload."""

    user_id: Optional[int] = None


# === Chat Schemas ===


class MessageCreate(BaseModel):
    """Schema for creating a message."""

    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""

    title: Optional[str] = "שיחה חדשה"


class ConversationResponse(BaseModel):
    """Schema for conversation response."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Schema for conversation with messages."""

    id: int
    title: str
    created_at: datetime
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat request."""

    message: str = Field(min_length=1)
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Schema for chat response."""

    response: str
    conversation_id: int
    message_id: int


# === Training Schemas ===


class TrainRequest(BaseModel):
    """Schema for training request."""

    content: str = Field(min_length=1)
    entry_type: str = "general"  # general, fact, qa, file


class TrainResponse(BaseModel):
    """Schema for training response."""

    success: bool
    message: str
    entry_id: Optional[int] = None


class TrainingEntryResponse(BaseModel):
    """Schema for training entry response."""

    id: int
    content: str
    entry_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# === Admin Schemas ===


class UserAdminUpdate(BaseModel):
    """Schema for admin updating user."""

    role: Optional[str] = None
    is_active: Optional[bool] = None


class SystemStats(BaseModel):
    """Schema for system statistics."""

    total_users: int
    active_users: int
    total_conversations: int
    total_messages: int
    total_training_entries: int
    knowledge_base_size: int
