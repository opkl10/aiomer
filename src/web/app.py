"""FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .api.routes import admin_router, auth_router, chat_router, user_router
from .api.routes.coding import router as coding_router
from .api.routes.blog import router as blog_router
from .config import get_settings
from .database import init_db

settings = get_settings()

# Paths
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="מערכת AI לשיחה, אימון וקבלת מידע",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# API routes
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(coding_router, prefix="/api")
app.include_router(blog_router, prefix="/api")


# Page routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Chat page."""
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """User dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin panel page."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/coding", response_class=HTMLResponse)
async def coding_page(request: Request):
    """Coding assistant page."""
    return templates.TemplateResponse("coding.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============== Blog Public Pages ==============

@app.get("/blog", response_class=HTMLResponse)
async def blog_home(request: Request):
    """Blog home page."""
    return templates.TemplateResponse("blog/index.html", {"request": request})


@app.get("/blog/post/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str):
    """Single blog post page."""
    return templates.TemplateResponse("blog/post.html", {"request": request, "slug": slug})


@app.get("/blog/category/{slug}", response_class=HTMLResponse)
async def blog_category(request: Request, slug: str):
    """Category page."""
    return templates.TemplateResponse("blog/category.html", {"request": request, "slug": slug})


@app.get("/blog/tag/{slug}", response_class=HTMLResponse)
async def blog_tag(request: Request, slug: str):
    """Tag page."""
    return templates.TemplateResponse("blog/tag.html", {"request": request, "slug": slug})


@app.get("/page/{slug}", response_class=HTMLResponse)
async def static_page(request: Request, slug: str):
    """Static page."""
    return templates.TemplateResponse("blog/page.html", {"request": request, "slug": slug})


# ============== Blog Admin Pages ==============

@app.get("/admin/blog", response_class=HTMLResponse)
async def admin_blog_dashboard(request: Request):
    """Blog admin dashboard."""
    return templates.TemplateResponse("blog/admin/dashboard.html", {"request": request})


@app.get("/admin/posts", response_class=HTMLResponse)
async def admin_posts(request: Request):
    """Manage posts."""
    return templates.TemplateResponse("blog/admin/posts.html", {"request": request})


@app.get("/admin/posts/new", response_class=HTMLResponse)
async def admin_new_post(request: Request):
    """Create new post."""
    return templates.TemplateResponse("blog/admin/post-editor.html", {"request": request})


@app.get("/admin/posts/{post_id}/edit", response_class=HTMLResponse)
async def admin_edit_post(request: Request, post_id: int):
    """Edit post."""
    return templates.TemplateResponse("blog/admin/post-editor.html", {"request": request, "post_id": post_id})


@app.get("/admin/pages", response_class=HTMLResponse)
async def admin_pages(request: Request):
    """Manage pages."""
    return templates.TemplateResponse("blog/admin/pages.html", {"request": request})


@app.get("/admin/pages/new", response_class=HTMLResponse)
async def admin_new_page(request: Request):
    """Create new page."""
    return templates.TemplateResponse("blog/admin/page-editor.html", {"request": request})


@app.get("/admin/pages/{page_id}/edit", response_class=HTMLResponse)
async def admin_edit_page(request: Request, page_id: int):
    """Edit page."""
    return templates.TemplateResponse("blog/admin/page-editor.html", {"request": request, "page_id": page_id})


@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request):
    """Manage categories."""
    return templates.TemplateResponse("blog/admin/categories.html", {"request": request})


@app.get("/admin/media", response_class=HTMLResponse)
async def admin_media(request: Request):
    """Media library."""
    return templates.TemplateResponse("blog/admin/media.html", {"request": request})


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    """Site settings."""
    return templates.TemplateResponse("blog/admin/settings.html", {"request": request})
