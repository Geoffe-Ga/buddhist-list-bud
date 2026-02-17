import pytest
from pymongo import MongoClient


def _get_ids():
    """Get known IDs from the real database."""
    client = MongoClient("mongodb://localhost:27017")
    db = client.buddhist_dhammas
    fnt = db.lists.find_one({"slug": "four-noble-truths"})
    first_dhamma = db.dhammas.find_one(
        {"parent_list_id": fnt["_id"], "position_in_list": 1}
    )
    # A list with upstream_from (has left-edge navigation)
    upstream_list = db.lists.find_one({"upstream_from": {"$ne": []}})
    return (
        str(fnt["_id"]),
        str(first_dhamma["_id"]),
        str(upstream_list["_id"]),
    )


LIST_ID, DHAMMA_ID, UPSTREAM_LIST_ID = _get_ids()


@pytest.mark.asyncio
async def test_navigate_list(client):
    resp = await client.get(f"/api/navigate/{LIST_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"]["type"] == "list"
    assert data["current"]["name"] == "Four Noble Truths"
    assert data["up"] is None
    assert data["down"] is None
    assert len(data["right"]) == 4


@pytest.mark.asyncio
async def test_navigate_dhamma(client):
    resp = await client.get(f"/api/navigate/{DHAMMA_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"]["type"] == "dhamma"
    assert data["up"] is None  # First item, no prev
    assert data["down"] is not None  # Has next sibling
    assert len(data["left"]) == 1  # Parent list


@pytest.mark.asyncio
async def test_navigate_invalid_id(client):
    resp = await client.get("/api/navigate/invalid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_navigate_nonexistent_id(client):
    resp = await client.get("/api/navigate/000000000000000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_navigate_dhamma_has_downstream_lists(client):
    """Downstream lists should appear on the right edge."""
    resp = await client.get(f"/api/navigate/{DHAMMA_ID}")
    data = resp.json()
    # First dhamma (There is Suffering) has downstream lists
    assert len(data["right"]) > 0
    assert data["right"][0]["type"] == "list"
    assert "children" not in data["right"][0]


@pytest.mark.asyncio
async def test_navigate_list_with_upstream(client):
    """A list with upstream_from should have left-edge dhammas."""
    resp = await client.get(f"/api/navigate/{UPSTREAM_LIST_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"]["type"] == "list"
    assert len(data["left"]) > 0
    assert data["left"][0]["type"] == "dhamma"
