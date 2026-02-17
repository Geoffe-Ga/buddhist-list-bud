import pytest


@pytest.mark.asyncio
async def test_get_all_lists(client):
    resp = await client.get("/api/lists")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 22
    assert all("name" in item for item in data)


@pytest.mark.asyncio
async def test_get_list_by_id(client):
    # First get all lists to find an ID
    resp = await client.get("/api/lists")
    first_id = resp.json()[0]["id"]

    resp = await client.get(f"/api/lists/{first_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "_id" in data
    assert "children" in data


@pytest.mark.asyncio
async def test_get_list_invalid_id(client):
    resp = await client.get("/api/lists/invalid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_list_not_found(client):
    resp = await client.get("/api/lists/000000000000000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_list_serializes_upstream(client):
    """Lists with upstream_from should serialize ref_ids as strings."""
    from pymongo import MongoClient

    mc = MongoClient("mongodb://localhost:27017")
    db = mc.buddhist_dhammas
    lst = db.lists.find_one({"upstream_from": {"$ne": []}})
    list_id = str(lst["_id"])

    resp = await client.get(f"/api/lists/{list_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["upstream_from"]) > 0
    assert isinstance(data["upstream_from"][0]["ref_id"], str)
