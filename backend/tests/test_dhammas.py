import pytest
from pymongo import MongoClient


def _get_dhamma_id():
    client = MongoClient("mongodb://localhost:27017")
    db = client.buddhist_dhammas
    d = db.dhammas.find_one({"slug": "right-concentration"})
    return str(d["_id"])


DHAMMA_ID = _get_dhamma_id()


@pytest.mark.asyncio
async def test_get_dhamma(client):
    resp = await client.get(f"/api/dhammas/{DHAMMA_ID}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["_id"] == DHAMMA_ID
    assert data["name"] == "Right Concentration"
    assert isinstance(data["parent_list_id"], str)
    assert isinstance(data["downstream"], list)


@pytest.mark.asyncio
async def test_get_dhamma_invalid_id(client):
    resp = await client.get("/api/dhammas/invalid")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_dhamma_not_found(client):
    resp = await client.get("/api/dhammas/000000000000000000000000")
    assert resp.status_code == 404
