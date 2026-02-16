import re

from fastapi import APIRouter, Query

from backend.app.db import get_db
from backend.app.models import SearchResult

router = APIRouter(prefix="/api")


@router.get("/search")
async def search(q: str = Query(default="")) -> list[SearchResult]:
    if len(q) < 2:
        return []

    db = get_db()
    pattern = re.escape(q)
    regex_filter = {
        "$or": [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"pali_name": {"$regex": pattern, "$options": "i"}},
        ]
    }
    projection = {"name": 1, "pali_name": 1}

    results: list[SearchResult] = []

    async for doc in db.lists.find(regex_filter, projection):
        results.append(
            SearchResult(
                id=str(doc["_id"]),
                name=doc["name"],
                pali_name=doc.get("pali_name", ""),
                type="list",
            )
        )

    async for doc in db.dhammas.find(regex_filter, projection):
        results.append(
            SearchResult(
                id=str(doc["_id"]),
                name=doc["name"],
                pali_name=doc.get("pali_name", ""),
                type="dhamma",
            )
        )

    results.sort(key=lambda r: r.name.lower())
    return results
