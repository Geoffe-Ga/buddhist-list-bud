from bson import ObjectId
from fastapi import APIRouter, HTTPException

from backend.app.db import get_db

router = APIRouter(prefix="/api")


@router.get("/dhammas/{dhamma_id}")
async def get_dhamma(dhamma_id: str) -> dict:
    if not ObjectId.is_valid(dhamma_id):
        raise HTTPException(status_code=404, detail="Invalid ID")

    db = get_db()
    doc = await db.dhammas.find_one({"_id": ObjectId(dhamma_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Dhamma not found")

    doc["_id"] = str(doc["_id"])
    doc["parent_list_id"] = str(doc["parent_list_id"])
    for ref in doc.get("downstream", []):
        ref["ref_id"] = str(ref["ref_id"])
    for ref in doc.get("upstream_from", []):
        ref["ref_id"] = str(ref["ref_id"])
    for ref in doc.get("cross_references", []):
        ref["ref_id"] = str(ref["ref_id"])
    return doc
