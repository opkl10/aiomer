"""API routes."""

from .admin import router as admin_router
from .auth import router as auth_router
from .chat import router as chat_router
from .user import router as user_router

__all__ = ["auth_router", "chat_router", "user_router", "admin_router"]
