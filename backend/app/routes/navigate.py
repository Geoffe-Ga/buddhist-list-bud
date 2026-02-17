from bson import ObjectId
from fastapi import APIRouter, HTTPException

from backend.app.db import get_db
from backend.app.models import CurrentNode, NavigateResponse, NodeSummary

router = APIRouter(prefix="/api")


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

    # Left: upstream dhammas — batch fetch all at once
    left: list[NodeSummary] = []
    upstream_ids = [ref["ref_id"] for ref in doc.get("upstream_from", [])]
    if upstream_ids:
        cursor = db.dhammas.find({"_id": {"$in": upstream_ids}}, {"name": 1})
        name_map = {d["_id"]: d["name"] async for d in cursor}
        for uid in upstream_ids:
            if uid in name_map:
                left.append(NodeSummary(id=str(uid), name=name_map[uid], type="dhamma"))

    # Right: children dhammas — batch fetch all at once
    right: list[NodeSummary] = []
    child_ids = doc.get("children", [])
    if child_ids:
        cursor = db.dhammas.find(
            {"_id": {"$in": child_ids}},
            {"name": 1, "position_in_list": 1},
        )
        child_map = {d["_id"]: d["name"] async for d in cursor}
        for cid in child_ids:
            if cid in child_map:
                right.append(
                    NodeSummary(id=str(cid), name=child_map[cid], type="dhamma")
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
    parent_id = doc["parent_list_id"]
    pos = doc.get("position_in_list", 0)

    # Batch: parent list + downstream lists in one query
    downstream_ids = [ref["ref_id"] for ref in doc.get("downstream", [])]
    all_list_ids = [parent_id, *downstream_ids]
    cursor = db.lists.find({"_id": {"$in": all_list_ids}}, {"name": 1})
    list_map = {d["_id"]: d["name"] async for d in cursor}

    # Left: parent list
    left: list[NodeSummary] = []
    if parent_id in list_map:
        left.append(
            NodeSummary(id=str(parent_id), name=list_map[parent_id], type="list")
        )

    # Right: downstream lists (preserve order)
    right: list[NodeSummary] = []
    for did in downstream_ids:
        if did in list_map:
            right.append(NodeSummary(id=str(did), name=list_map[did], type="list"))

    # Up/Down siblings — single query fetching both neighbors
    siblings = db.dhammas.find(
        {
            "parent_list_id": parent_id,
            "position_in_list": {"$in": [pos - 1, pos + 1]},
        },
        {"name": 1, "position_in_list": 1},
    )
    up_node = None
    down_node = None
    async for sib in siblings:
        summary = NodeSummary(id=str(sib["_id"]), name=sib["name"])
        if sib["position_in_list"] == pos - 1:
            up_node = summary
        else:
            down_node = summary

    return NavigateResponse(
        current=CurrentNode(
            id=str(doc["_id"]),
            type="dhamma",
            name=doc["name"],
            pali_name=doc.get("pali_name", ""),
            essay=doc.get("essay"),
        ),
        up=up_node,
        down=down_node,
        left=left,
        right=right,
    )
