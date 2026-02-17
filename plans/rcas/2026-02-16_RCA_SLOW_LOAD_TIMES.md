# RCA: Slow Load Times

**Date**: 2026-02-16
**Severity**: High
**Component**: Backend (FastAPI + MongoDB)

## Problem Statement

Page loads and navigation clicks are noticeably slow. The app feels sluggish despite having only ~140 documents total in MongoDB.

## Root Cause

Three compounding issues:

### 1. New MongoDB connection on every request (db.py:8-12) — PRIMARY

```python
def get_client() -> AsyncIOMotorClient:
    global _client
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    _client = AsyncIOMotorClient(uri)  # Creates NEW client every call
    return _client
```

The `_client` global is overwritten on every call with no `if _client is None` guard. Each request triggers a full connection negotiation: TCP handshake, TLS/SSL handshake (for Atlas SRV), SCRAM authentication. This adds **100-500ms per request**.

### 2. N+1 queries in /navigate endpoint (navigate.py:42-108)

The navigate endpoint fires sequential `find_one()` calls in loops:
- `_navigate_list`: 1 (list) + N (upstream names) + M (child names) = **1+N+M queries**
- `_navigate_dhamma`: 1 (dhamma) + 1 (parent) + K (downstream) + 2 (siblings) = **4+K queries**

For a typical list with 8 items and 3 upstream refs, that's **12 sequential roundtrips**. At ~50ms each over the network to Atlas, that's **600ms** just for this endpoint.

### 3. Missing composite indexes

The sibling lookup query `{parent_list_id, position_in_list}` has no compound index, forcing a collection scan on every navigate call.

## Analysis

The connection issue was introduced when `db.py` was first written — the singleton guard was simply never added. The N+1 pattern is a common oversight when building endpoints incrementally (each query looks fine in isolation). The missing indexes weren't caught because the dataset is tiny so scans are fast locally, but add latency over the network.

## Impact

- Every page load: ~1-3 seconds (should be <200ms)
- Every navigation click: ~0.5-1.5 seconds
- Search: ~200-500ms (should be <100ms)

## Fix Strategy

| Fix | File | Expected Impact |
|-----|------|----------------|
| Singleton connection guard | db.py | 50-80% latency reduction |
| Batch queries with `$in` | navigate.py | 70-90% reduction on navigate |
| Add compound indexes | seed_db.py + startup | 30-50% on sibling lookups |

## Prevention

- Add a startup health check that verifies connection reuse
- Load test endpoints during development (`time curl` or similar)
- Review query count per endpoint as part of code review
