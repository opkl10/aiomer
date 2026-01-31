"""
Blog API routes - Posts, Pages, Categories, Tags, Settings, Media.
"""

import os
import re
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...auth import get_current_user, get_current_admin
from ...database import get_db
from ...models import (
    User, Post, Page, Category, Tag, Comment, Media, SiteSettings, PostStatus
)


router = APIRouter(prefix="/blog", tags=["blog"])


# ============== Pydantic Schemas ==============

class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    color: str = "#3498db"
    parent_id: Optional[int] = None
    order: int = 0


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[int] = None
    order: Optional[int] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str]
    color: str
    parent_id: Optional[int]
    order: int
    post_count: int = 0

    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str
    slug: Optional[str] = None


class TagResponse(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: str
    featured_image: Optional[str] = None
    status: str = PostStatus.DRAFT.value
    category_id: Optional[int] = None
    tag_ids: list[int] = []
    is_featured: bool = False
    allow_comments: bool = True
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    published_at: Optional[datetime] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    featured_image: Optional[str] = None
    status: Optional[str] = None
    category_id: Optional[int] = None
    tag_ids: Optional[list[int]] = None
    is_featured: Optional[bool] = None
    allow_comments: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    published_at: Optional[datetime] = None


class PostResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str]
    content: str
    featured_image: Optional[str]
    status: str
    author_id: int
    author_name: str = ""
    category_id: Optional[int]
    category_name: Optional[str] = None
    tags: list[TagResponse] = []
    views: int
    is_featured: bool
    allow_comments: bool
    meta_title: Optional[str]
    meta_description: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PageCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    content: str
    status: str = PostStatus.DRAFT.value
    template: str = "default"
    show_in_menu: bool = False
    menu_order: int = 0
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class PageUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    template: Optional[str] = None
    show_in_menu: Optional[bool] = None
    menu_order: Optional[int] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class PageResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    status: str
    author_id: int
    author_name: str = ""
    template: str
    show_in_menu: bool
    menu_order: int
    meta_title: Optional[str]
    meta_description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    post_id: int
    author_name: str
    author_email: str
    content: str
    parent_id: Optional[int] = None


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: Optional[int]
    author_name: str
    author_email: str
    content: str
    is_approved: bool
    parent_id: Optional[int]
    created_at: datetime
    replies: list["CommentResponse"] = []

    class Config:
        from_attributes = True


class SiteSettingsUpdate(BaseModel):
    site_name: Optional[str] = None
    site_description: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    footer_text: Optional[str] = None
    social_facebook: Optional[str] = None
    social_twitter: Optional[str] = None
    social_instagram: Optional[str] = None
    social_linkedin: Optional[str] = None
    social_github: Optional[str] = None
    google_analytics_id: Optional[str] = None
    posts_per_page: Optional[int] = None
    enable_comments: Optional[bool] = None
    enable_ai_assistant: Optional[bool] = None
    custom_css: Optional[str] = None
    custom_head: Optional[str] = None


class SiteSettingsResponse(BaseModel):
    id: int
    site_name: str
    site_description: Optional[str]
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: str
    secondary_color: str
    footer_text: Optional[str]
    social_facebook: Optional[str]
    social_twitter: Optional[str]
    social_instagram: Optional[str]
    social_linkedin: Optional[str]
    social_github: Optional[str]
    google_analytics_id: Optional[str]
    posts_per_page: int
    enable_comments: bool
    enable_ai_assistant: bool
    custom_css: Optional[str]
    custom_head: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class MediaResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_type: str
    mime_type: str
    file_size: int
    alt_text: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Helper Functions ==============

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Handle Hebrew and other non-ASCII
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text or f"post-{uuid.uuid4().hex[:8]}"


async def get_or_create_settings(db: AsyncSession) -> SiteSettings:
    """Get or create site settings."""
    result = await db.execute(select(SiteSettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = SiteSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


# ============== Site Settings Routes ==============

@router.get("/settings", response_model=SiteSettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get site settings (public)."""
    return await get_or_create_settings(db)


@router.put("/settings", response_model=SiteSettingsResponse)
async def update_settings(
    data: SiteSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update site settings (admin only)."""
    settings = await get_or_create_settings(db)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings


# ============== Category Routes ==============

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all categories."""
    result = await db.execute(
        select(Category).order_by(Category.order, Category.name)
    )
    categories = result.scalars().all()

    response = []
    for cat in categories:
        # Count posts
        count_result = await db.execute(
            select(func.count(Post.id)).where(
                Post.category_id == cat.id,
                Post.status == PostStatus.PUBLISHED.value
            )
        )
        post_count = count_result.scalar() or 0

        response.append(CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            description=cat.description,
            color=cat.color,
            parent_id=cat.parent_id,
            order=cat.order,
            post_count=post_count
        ))

    return response


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a new category."""
    slug = data.slug or slugify(data.name)

    # Check if slug exists
    existing = await db.execute(select(Category).where(Category.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        color=data.color,
        parent_id=data.parent_id,
        order=data.order
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        parent_id=category.parent_id,
        order=category.order,
        post_count=0
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update a category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        color=category.color,
        parent_id=category.parent_id,
        order=category.order,
        post_count=0
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a category."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(category)
    await db.commit()
    return {"message": "Category deleted"}


# ============== Tag Routes ==============

@router.get("/tags", response_model=list[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """List all tags."""
    result = await db.execute(select(Tag).order_by(Tag.name))
    return result.scalars().all()


@router.post("/tags", response_model=TagResponse)
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a new tag."""
    slug = data.slug or slugify(data.name)

    existing = await db.execute(select(Tag).where(Tag.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    tag = Tag(name=data.name, slug=slug)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a tag."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    await db.delete(tag)
    await db.commit()
    return {"message": "Tag deleted"}


# ============== Post Routes ==============

@router.get("/posts", response_model=dict)
async def list_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List posts with pagination and filters."""
    query = select(Post).options(
        selectinload(Post.author),
        selectinload(Post.category),
        selectinload(Post.tags)
    )

    # Filters
    if status:
        query = query.where(Post.status == status)
    if category_id:
        query = query.where(Post.category_id == category_id)
    if featured_only:
        query = query.where(Post.is_featured == True)
    if search:
        query = query.where(
            or_(
                Post.title.ilike(f"%{search}%"),
                Post.content.ilike(f"%{search}%")
            )
        )
    if tag_id:
        query = query.join(Post.tags).where(Tag.id == tag_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Pagination
    query = query.order_by(Post.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "posts": [
            PostResponse(
                id=p.id,
                title=p.title,
                slug=p.slug,
                excerpt=p.excerpt,
                content=p.content,
                featured_image=p.featured_image,
                status=p.status,
                author_id=p.author_id,
                author_name=p.author.full_name or p.author.username if p.author else "",
                category_id=p.category_id,
                category_name=p.category.name if p.category else None,
                tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in p.tags],
                views=p.views,
                is_featured=p.is_featured,
                allow_comments=p.allow_comments,
                meta_title=p.meta_title,
                meta_description=p.meta_description,
                published_at=p.published_at,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in posts
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/posts/{slug}", response_model=PostResponse)
async def get_post(
    slug: str,
    db: AsyncSession = Depends(get_db),
    increment_views: bool = True
):
    """Get a single post by slug."""
    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.tags)
        )
        .where(Post.slug == slug)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Increment views
    if increment_views:
        post.views += 1
        await db.commit()

    return PostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content,
        featured_image=post.featured_image,
        status=post.status,
        author_id=post.author_id,
        author_name=post.author.full_name or post.author.username if post.author else "",
        category_id=post.category_id,
        category_name=post.category.name if post.category else None,
        tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in post.tags],
        views=post.views,
        is_featured=post.is_featured,
        allow_comments=post.allow_comments,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at
    )


@router.post("/posts", response_model=PostResponse)
async def create_post(
    data: PostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Create a new post."""
    slug = data.slug or slugify(data.title)

    # Check if slug exists
    existing = await db.execute(select(Post).where(Post.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    # Set published_at if publishing
    published_at = data.published_at
    if data.status == PostStatus.PUBLISHED.value and not published_at:
        published_at = datetime.utcnow()

    post = Post(
        title=data.title,
        slug=slug,
        excerpt=data.excerpt,
        content=data.content,
        featured_image=data.featured_image,
        status=data.status,
        author_id=user.id,
        category_id=data.category_id,
        is_featured=data.is_featured,
        allow_comments=data.allow_comments,
        meta_title=data.meta_title,
        meta_description=data.meta_description,
        published_at=published_at
    )

    # Add tags
    if data.tag_ids:
        result = await db.execute(select(Tag).where(Tag.id.in_(data.tag_ids)))
        tags = result.scalars().all()
        post.tags = list(tags)

    db.add(post)
    await db.commit()
    await db.refresh(post)

    # Reload with relationships
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags))
        .where(Post.id == post.id)
    )
    post = result.scalar_one()

    return PostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content,
        featured_image=post.featured_image,
        status=post.status,
        author_id=post.author_id,
        author_name=post.author.full_name or post.author.username if post.author else "",
        category_id=post.category_id,
        category_name=post.category.name if post.category else None,
        tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in post.tags],
        views=post.views,
        is_featured=post.is_featured,
        allow_comments=post.allow_comments,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at
    )


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Update a post."""
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.tags))
        .where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tag_ids" in update_data:
        tag_ids = update_data.pop("tag_ids")
        result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        post.tags = list(result.scalars().all())

    # Set published_at if publishing for first time
    if update_data.get("status") == PostStatus.PUBLISHED.value and not post.published_at:
        update_data["published_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()

    # Reload
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags))
        .where(Post.id == post.id)
    )
    post = result.scalar_one()

    return PostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        excerpt=post.excerpt,
        content=post.content,
        featured_image=post.featured_image,
        status=post.status,
        author_id=post.author_id,
        author_name=post.author.full_name or post.author.username if post.author else "",
        category_id=post.category_id,
        category_name=post.category.name if post.category else None,
        tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in post.tags],
        views=post.views,
        is_featured=post.is_featured,
        allow_comments=post.allow_comments,
        meta_title=post.meta_title,
        meta_description=post.meta_description,
        published_at=post.published_at,
        created_at=post.created_at,
        updated_at=post.updated_at
    )


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Delete a post."""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.delete(post)
    await db.commit()
    return {"message": "Post deleted"}


# ============== Page Routes ==============

@router.get("/pages", response_model=list[PageResponse])
async def list_pages(
    status: Optional[str] = None,
    menu_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all pages."""
    query = select(Page).options(selectinload(Page.author))

    if status:
        query = query.where(Page.status == status)
    if menu_only:
        query = query.where(Page.show_in_menu == True)

    query = query.order_by(Page.menu_order, Page.title)
    result = await db.execute(query)
    pages = result.scalars().all()

    return [
        PageResponse(
            id=p.id,
            title=p.title,
            slug=p.slug,
            content=p.content,
            status=p.status,
            author_id=p.author_id,
            author_name=p.author.full_name or p.author.username if p.author else "",
            template=p.template,
            show_in_menu=p.show_in_menu,
            menu_order=p.menu_order,
            meta_title=p.meta_title,
            meta_description=p.meta_description,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in pages
    ]


@router.get("/pages/{slug}", response_model=PageResponse)
async def get_page(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single page by slug."""
    result = await db.execute(
        select(Page).options(selectinload(Page.author)).where(Page.slug == slug)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return PageResponse(
        id=page.id,
        title=page.title,
        slug=page.slug,
        content=page.content,
        status=page.status,
        author_id=page.author_id,
        author_name=page.author.full_name or page.author.username if page.author else "",
        template=page.template,
        show_in_menu=page.show_in_menu,
        menu_order=page.menu_order,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        created_at=page.created_at,
        updated_at=page.updated_at
    )


@router.post("/pages", response_model=PageResponse)
async def create_page(
    data: PageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Create a new page."""
    slug = data.slug or slugify(data.title)

    existing = await db.execute(select(Page).where(Page.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    page = Page(
        title=data.title,
        slug=slug,
        content=data.content,
        status=data.status,
        author_id=user.id,
        template=data.template,
        show_in_menu=data.show_in_menu,
        menu_order=data.menu_order,
        meta_title=data.meta_title,
        meta_description=data.meta_description
    )

    db.add(page)
    await db.commit()
    await db.refresh(page)

    result = await db.execute(
        select(Page).options(selectinload(Page.author)).where(Page.id == page.id)
    )
    page = result.scalar_one()

    return PageResponse(
        id=page.id,
        title=page.title,
        slug=page.slug,
        content=page.content,
        status=page.status,
        author_id=page.author_id,
        author_name=page.author.full_name or page.author.username if page.author else "",
        template=page.template,
        show_in_menu=page.show_in_menu,
        menu_order=page.menu_order,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        created_at=page.created_at,
        updated_at=page.updated_at
    )


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: int,
    data: PageUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Update a page."""
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(page, field, value)

    await db.commit()

    result = await db.execute(
        select(Page).options(selectinload(Page.author)).where(Page.id == page.id)
    )
    page = result.scalar_one()

    return PageResponse(
        id=page.id,
        title=page.title,
        slug=page.slug,
        content=page.content,
        status=page.status,
        author_id=page.author_id,
        author_name=page.author.full_name or page.author.username if page.author else "",
        template=page.template,
        show_in_menu=page.show_in_menu,
        menu_order=page.menu_order,
        meta_title=page.meta_title,
        meta_description=page.meta_description,
        created_at=page.created_at,
        updated_at=page.updated_at
    )


@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Delete a page."""
    result = await db.execute(select(Page).where(Page.id == page_id))
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    await db.delete(page)
    await db.commit()
    return {"message": "Page deleted"}


# ============== Comment Routes ==============

@router.get("/posts/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    post_id: int,
    approved_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List comments for a post."""
    query = select(Comment).where(
        Comment.post_id == post_id,
        Comment.parent_id == None
    )

    if approved_only:
        query = query.where(Comment.is_approved == True)

    query = query.order_by(Comment.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/comments", response_model=CommentResponse)
async def create_comment(
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = None
):
    """Create a new comment."""
    # Verify post exists
    post_result = await db.execute(select(Post).where(Post.id == data.post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.allow_comments:
        raise HTTPException(status_code=400, detail="Comments are disabled for this post")

    comment = Comment(
        post_id=data.post_id,
        user_id=user.id if user else None,
        author_name=data.author_name,
        author_email=data.author_email,
        content=data.content,
        parent_id=data.parent_id,
        is_approved=user.is_admin if user else False
    )

    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


@router.put("/comments/{comment_id}/approve")
async def approve_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Approve a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.is_approved = True
    await db.commit()
    return {"message": "Comment approved"}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    await db.delete(comment)
    await db.commit()
    return {"message": "Comment deleted"}


# ============== Media Routes ==============

UPLOAD_DIR = Path(__file__).parent.parent.parent.parent / "uploads"
ALLOWED_TYPES = {
    "image": ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"],
    "video": ["video/mp4", "video/webm"],
    "document": ["application/pdf", "text/plain", "application/msword"]
}


@router.post("/media/upload", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    alt_text: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Upload a media file."""
    # Determine file type
    mime_type = file.content_type or "application/octet-stream"
    file_type = "document"
    for ftype, mimes in ALLOWED_TYPES.items():
        if mime_type in mimes:
            file_type = ftype
            break

    # Create upload directory
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    ext = Path(file.filename or "file").suffix
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / filename

    # Save file
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Get file size
    file_size = file_path.stat().st_size

    # Create database entry
    media = Media(
        filename=filename,
        original_filename=file.filename or "file",
        file_path=f"/uploads/{filename}",
        file_type=file_type,
        mime_type=mime_type,
        file_size=file_size,
        alt_text=alt_text,
        uploaded_by=user.id
    )

    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


@router.get("/media", response_model=list[MediaResponse])
async def list_media(
    file_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """List all media files."""
    query = select(Media).order_by(Media.created_at.desc())
    if file_type:
        query = query.where(Media.file_type == file_type)

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/media/{media_id}")
async def delete_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Delete a media file."""
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete file from disk
    file_path = UPLOAD_DIR / media.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(media)
    await db.commit()
    return {"message": "Media deleted"}


# ============== Stats Route ==============

@router.get("/stats")
async def get_blog_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_admin)
):
    """Get blog statistics."""
    posts_count = (await db.execute(select(func.count(Post.id)))).scalar() or 0
    published_posts = (await db.execute(
        select(func.count(Post.id)).where(Post.status == PostStatus.PUBLISHED.value)
    )).scalar() or 0
    pages_count = (await db.execute(select(func.count(Page.id)))).scalar() or 0
    categories_count = (await db.execute(select(func.count(Category.id)))).scalar() or 0
    tags_count = (await db.execute(select(func.count(Tag.id)))).scalar() or 0
    comments_count = (await db.execute(select(func.count(Comment.id)))).scalar() or 0
    pending_comments = (await db.execute(
        select(func.count(Comment.id)).where(Comment.is_approved == False)
    )).scalar() or 0
    total_views = (await db.execute(select(func.sum(Post.views)))).scalar() or 0

    return {
        "posts": posts_count,
        "published_posts": published_posts,
        "pages": pages_count,
        "categories": categories_count,
        "tags": tags_count,
        "comments": comments_count,
        "pending_comments": pending_comments,
        "total_views": total_views
    }
