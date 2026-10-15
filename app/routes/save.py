"""
POST /api/save — the one-click save used by the browser extension.

Unlike POST /api/resources/, it never refuses a page for being long or already
saved: the URL is normalized, an existing link is returned as it is (200), a new
one is created (201), and long titles and notes are cut to fit.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import resource_crud
from app.database import get_db
from app.models import Resource as ResourceModel
from app.schemas import Resource
from app.services import metadata
from app.services.urls import UnsupportedURLError, fallback_title, normalize_url

router = APIRouter(prefix="/api", tags=["save"])

TITLE_MAX, NOTE_MAX, CATEGORY_MAX = 200, 1000, 100


class SaveRequest(BaseModel):
    url: str = Field(..., max_length=4000, description="The page to save, as the browser has it")
    title: Optional[str] = Field(None, max_length=4000, description="The tab title; cut to 200 characters")
    note: Optional[str] = Field(None, max_length=10000, description="Optional note; cut to 1000 characters")
    category: Optional[str] = Field(None, max_length=CATEGORY_MAX)


class SaveResponse(BaseModel):
    resource: Resource
    created: bool = Field(..., description="False when the link was already in the library")


def _clip(text: Optional[str], limit: int) -> Optional[str]:
    text = " ".join((text or "").split())
    return (text[: limit - 1] + "…" if len(text) > limit else text) or None


@router.post(
    "/save",
    response_model=SaveResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": SaveResponse, "description": "Already saved; nothing changed"},
               422: {"description": "Not an http(s) page"}},
)
async def save(
    body: SaveRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SaveResponse:
    try:
        url = normalize_url(body.url)
    except UnsupportedURLError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if len(url) > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="This address is longer than 500 characters and can't be saved.")

    existing = await resource_crud.get_by_url(db, url)
    if existing:
        response.status_code = status.HTTP_200_OK
        return SaveResponse(resource=Resource.model_validate(existing), created=False)

    row = ResourceModel(
        url=url,
        title=_clip(body.title, TITLE_MAX) or _clip(fallback_title(url), TITLE_MAX),
        description=_clip(body.note, NOTE_MAX),
        category=_clip(body.category, CATEGORY_MAX),
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:  # saved by another request a moment ago
        await db.rollback()
        existing = await resource_crud.get_by_url(db, url)
        response.status_code = status.HTTP_200_OK
        return SaveResponse(resource=Resource.model_validate(existing), created=False)
    await db.refresh(row)
    background_tasks.add_task(metadata.refresh_resource_metadata, row.id, row.url)
    return SaveResponse(resource=Resource.model_validate(row), created=True)
