from typing import Optional

from fastapi import APIRouter, Query

from app.services.publishing import get_current_catalogue, search_catalogue

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
def get_catalogue() -> dict:
    return get_current_catalogue()


@router.get("/catalog/search")
def search_catalog(
    q: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None),
    section: Optional[str] = Query(default=None),
) -> list[dict]:
    return search_catalogue(q, category, language, section)
