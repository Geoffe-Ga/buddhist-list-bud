# RCA: Downstream Refs Resolve to Dhamma IDs Instead of List IDs

**Date**: 2026-02-16
**Severity**: High — data corruption affects navigation for multiple nodes
**Status**: In Progress

## Problem Statement

"There is a Path to the End of Suffering" (and likely other dhammas) shows only 4 downstream lists on the right panel instead of 8. The missing lists — Noble Eightfold Path, Four Right Efforts, Four Foundations of Mindfulness, Seven Factors of Awakening — are present in the database but their downstream refs point to dhamma ObjectIds instead of list ObjectIds.

## Root Cause

`seed_db.py` line 759:
```python
slug_to_id = {**list_slug_to_id, **dhamma_slug_to_id}
```

This merges both lookup tables into one dict. When a dhamma and a list share the same slug (e.g., `noble-eightfold-path`), the dhamma ID overwrites the list ID because dhamma entries come second.

Line 794 then uses this merged dict to resolve downstream refs:
```python
ref_id = slug_to_id.get(ref.get("ref_slug"))
```

Since downstream refs from dhammas always point to lists, this should use `list_slug_to_id` — not the merged `slug_to_id`.

## Analysis

The `ref_type` field in downstream refs already tells us what collection the target belongs to. Instead of using the ambiguous merged dict, we should dispatch based on `ref_type`:
- `ref_type == "list"` → use `list_slug_to_id`
- `ref_type == "dhamma"` → use `dhamma_slug_to_id`

The same issue potentially affects `upstream_from_slugs` resolution on lines 770 and 806, which also use the merged `slug_to_id`.

## Impact

- 4 of 8 downstream lists missing from "There is a Path to the End of Suffering"
- Any dhamma-list slug collision causes wrong ObjectId resolution
- Navigation graph is broken for affected nodes

## Contributing Factors

- No validation that resolved ObjectIds actually exist in the expected collection
- The merged `slug_to_id` dict was a convenience that masked the collision
- No tests covering the seeding logic

## Fix Strategy

Replace all uses of the merged `slug_to_id` with type-aware lookups:
```python
def resolve_ref(ref):
    if ref["ref_type"] == "list":
        return list_slug_to_id.get(ref.get("ref_slug"))
    return dhamma_slug_to_id.get(ref.get("ref_slug"))
```

Then re-seed the Atlas database.

## Prevention

- Add a warning/assertion when slug collisions are detected between collections
- Add a seed verification step that checks all ref ObjectIds exist in the correct collection
