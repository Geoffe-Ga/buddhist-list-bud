from bson import ObjectId
from fastapi import APIRouter, HTTPException

from backend.app.db import get_db
from backend.app.models import ListSummary

router = APIRouter(prefix="/api")


@router.get("/lists")
async def get_lists() -> list[ListSummary]:
    db = get_db()
    cursor = db.lists.find(
        {}, {"name": 1, "pali_name": 1, "slug": 1, "item_count": 1}
    ).sort("name", 1)
    results = []
    async for doc in cursor:
        results.append(
            ListSummary(
                id=str(doc["_id"]),
                name=doc["name"],
                pali_name=doc.get("pali_name", ""),
                slug=doc.get("slug", ""),
                item_count=doc.get("item_count", 0),
            )
        )
    return results


@router.get("/lists/{list_id}")
async def get_list(list_id: str) -> dict:
    if not ObjectId.is_valid(list_id):
        raise HTTPException(status_code=404, detail="Invalid ID")

    db = get_db()
    doc = await db.lists.find_one({"_id": ObjectId(list_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="List not found")

    doc["_id"] = str(doc["_id"])
    doc["children"] = [str(c) for c in doc.get("children", [])]
    for ref in doc.get("upstream_from", []):
        ref["ref_id"] = str(ref["ref_id"])
    return doc
