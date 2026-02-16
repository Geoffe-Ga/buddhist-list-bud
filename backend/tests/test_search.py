import pytest


@pytest.mark.asyncio
async def test_search_by_english_name(client):
    resp = await client.get("/api/search", params={"q": "noble"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert any("Noble" in r["name"] for r in results)


@pytest.mark.asyncio
async def test_search_by_pali_name(client):
    resp = await client.get("/api/search", params={"q": "dukkha"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    assert any("dukkha" in r["pali_name"].lower() for r in results)


@pytest.mark.asyncio
async def test_search_empty_query(client):
    resp = await client.get("/api/search", params={"q": ""})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_short_query(client):
    resp = await client.get("/api/search", params={"q": "a"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_no_query_param(client):
    resp = await client.get("/api/search")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_search_includes_both_types(client):
    resp = await client.get("/api/search", params={"q": "suffering"})
    assert resp.status_code == 200
    results = resp.json()
    types = {r["type"] for r in results}
    # "suffering" should match at least a dhamma
    assert "dhamma" in types or "list" in types


@pytest.mark.asyncio
async def test_search_results_sorted_alphabetically(client):
    resp = await client.get("/api/search", params={"q": "the"})
    assert resp.status_code == 200
    results = resp.json()
    if len(results) > 1:
        names = [r["name"].lower() for r in results]
        assert names == sorted(names)


@pytest.mark.asyncio
async def test_search_result_shape(client):
    resp = await client.get("/api/search", params={"q": "noble"})
    results = resp.json()
    assert len(results) > 0
    result = results[0]
    assert "id" in result
    assert "name" in result
    assert "pali_name" in result
    assert "type" in result
