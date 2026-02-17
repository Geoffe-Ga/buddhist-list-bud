from bson import ObjectId
from fastapi import APIRouter, HTTPException

from backend.app.db import get_db
from backend.app.models import CurrentNode, NavigateResponse, NodeSummary

router = APIRouter(prefix="/api")


async def _resolve_name(collection: str, oid: ObjectId) -> str | None:
    doc = await get_db()[collection].find_one({"_id": oid}, {"name": 1})
    return doc["name"] if doc else None


@router.get("/navigate/{node_id}")
async def navigate(node_id: str) -> NavigateResponse:
    db = get_db()

    if not ObjectId.is_valid(node_id):
        raise HTTPException(status_code=404, detail="Invalid ID")

    oid = ObjectId(node_id)

    # Try lists first
    list_doc = await db.lists.find_one({"_id": oid})
    if list_doc:
        return await _navigate_list(list_doc)

    # Try dhammas
    dhamma_doc = await db.dhammas.find_one({"_id": oid})
    if dhamma_doc:
        return await _navigate_dhamma(dhamma_doc)

    raise HTTPException(status_code=404, detail="Node not found")


async def _navigate_list(doc: dict) -> NavigateResponse:
    db = get_db()

    # Left: upstream dhammas (dhammas that zoom into this list)
    left: list[NodeSummary] = []
    for ref in doc.get("upstream_from", []):
        name = await _resolve_name("dhammas", ref["ref_id"])
        if name:
            left.append(NodeSummary(id=str(ref["ref_id"]), name=name, type="dhamma"))

    # Right: children dhammas
    right: list[NodeSummary] = []
    for child_id in doc.get("children", []):
        child = await db.dhammas.find_one(
            {"_id": child_id}, {"name": 1, "position_in_list": 1}
        )
        if child:
            right.append(
                NodeSummary(id=str(child_id), name=child["name"], type="dhamma")
            )

    return NavigateResponse(
        current=CurrentNode(
            id=str(doc["_id"]),
            type="list",
            name=doc["name"],
            pali_name=doc.get("pali_name", ""),
            description=doc.get("description"),
        ),
        up=None,
        down=None,
        left=left,
        right=right,
    )


async def _navigate_dhamma(doc: dict) -> NavigateResponse:
    db = get_db()

    # Left: parent list
    left: list[NodeSummary] = []
    parent = await db.lists.find_one({"_id": doc["parent_list_id"]}, {"name": 1})
    if parent:
        left.append(
            NodeSummary(id=str(parent["_id"]), name=parent["name"], type="list")
        )

    # Right: downstream lists
    right: list[NodeSummary] = []
    for ref in doc.get("downstream", []):
        list_doc = await db.lists.find_one({"_id": ref["ref_id"]}, {"name": 1})
        if list_doc:
            right.append(
                NodeSummary(
                    id=str(ref["ref_id"]),
                    name=list_doc["name"],
                    type="list",
                )
            )

    # Up/Down: siblings by position_in_list
    pos = doc.get("position_in_list", 0)
    parent_id = doc["parent_list_id"]

    up_doc = await db.dhammas.find_one(
        {"parent_list_id": parent_id, "position_in_list": pos - 1},
        {"name": 1},
    )
    down_doc = await db.dhammas.find_one(
        {"parent_list_id": parent_id, "position_in_list": pos + 1},
        {"name": 1},
    )

    return NavigateResponse(
        current=CurrentNode(
            id=str(doc["_id"]),
            type="dhamma",
            name=doc["name"],
            pali_name=doc.get("pali_name", ""),
            essay=doc.get("essay"),
        ),
        up=(
            NodeSummary(id=str(up_doc["_id"]), name=up_doc["name"]) if up_doc else None
        ),
        down=(
            NodeSummary(id=str(down_doc["_id"]), name=down_doc["name"])
            if down_doc
            else None
        ),
        left=left,
        right=right,
    )
