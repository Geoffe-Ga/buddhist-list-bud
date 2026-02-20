from bson import ObjectId
from fastapi import APIRouter, HTTPException

from backend.app.db import get_db
from backend.app.models import CurrentNode, NavigateResponse, NodeSummary

router = APIRouter(prefix="/api")

MAX_BREADCRUMB_DEPTH = 20


async def _build_breadcrumbs(node_id: ObjectId, node_type: str) -> list[NodeSummary]:
    """Walk up the parent chain to build root-to-current path."""
    db = get_db()
    crumbs: list[NodeSummary] = []
    cur_id = node_id
    cur_type = node_type

    for _ in range(MAX_BREADCRUMB_DEPTH):
        if cur_type == "dhamma":
            doc = await db.dhammas.find_one(
                {"_id": cur_id}, {"name": 1, "parent_list_id": 1}
            )
            if not doc:
                break
            crumbs.append(NodeSummary(id=str(cur_id), name=doc["name"], type="dhamma"))
            cur_id = doc["parent_list_id"]
            cur_type = "list"
        else:
            doc = await db.lists.find_one(
                {"_id": cur_id}, {"name": 1, "upstream_from": 1}
            )
            if not doc:
                break
            crumbs.append(NodeSummary(id=str(cur_id), name=doc["name"], type="list"))
            upstream = doc.get("upstream_from", [])
            if not upstream:
                break
            cur_id = upstream[0]["ref_id"]
            cur_type = "dhamma"

    crumbs.reverse()
    # Remove the last element (current node) — it's shown in the content area
    if crumbs:
        crumbs.pop()
    return crumbs


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

    breadcrumbs = await _build_breadcrumbs(doc["_id"], "list")

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
        breadcrumbs=breadcrumbs,
    )


async def _navigate_dhamma(doc: dict) -> NavigateResponse:
    db = get_db()
    parent_id = doc["parent_list_id"]
    pos = doc.get("position_in_list", 0)

    # Separate downstream refs by type (list vs dhamma)
    downstream_refs = doc.get("downstream", [])
    downstream_list_ids = [
        ref["ref_id"] for ref in downstream_refs if ref.get("ref_type") == "list"
    ]
    downstream_dhamma_ids = [
        ref["ref_id"] for ref in downstream_refs if ref.get("ref_type") == "dhamma"
    ]

    # Batch fetch: parent list + downstream lists
    all_list_ids = [parent_id, *downstream_list_ids]
    cursor = db.lists.find({"_id": {"$in": all_list_ids}}, {"name": 1})
    list_map = {d["_id"]: d["name"] async for d in cursor}

    # Batch fetch: downstream dhammas
    dhamma_map: dict = {}
    if downstream_dhamma_ids:
        cursor = db.dhammas.find({"_id": {"$in": downstream_dhamma_ids}}, {"name": 1})
        dhamma_map = {d["_id"]: d["name"] async for d in cursor}

    # Left: parent list
    left: list[NodeSummary] = []
    if parent_id in list_map:
        left.append(
            NodeSummary(id=str(parent_id), name=list_map[parent_id], type="list")
        )

    # Right: downstream refs (preserve order, mixed list/dhamma types)
    right: list[NodeSummary] = []
    for ref in downstream_refs:
        rid = ref["ref_id"]
        rtype = ref.get("ref_type", "list")
        if rtype == "list" and rid in list_map:
            right.append(NodeSummary(id=str(rid), name=list_map[rid], type="list"))
        elif rtype == "dhamma" and rid in dhamma_map:
            right.append(NodeSummary(id=str(rid), name=dhamma_map[rid], type="dhamma"))

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

    breadcrumbs = await _build_breadcrumbs(doc["_id"], "dhamma")

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
        breadcrumbs=breadcrumbs,
    )
