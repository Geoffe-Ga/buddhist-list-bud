#!/usr/bin/env python3
"""
query_examples.py — Demonstrate common query patterns for the Buddhist Dhammas graph.

This script shows how to navigate the fractal knowledge graph using MongoDB
queries. Each example demonstrates a different relationship type or traversal
pattern that a frontend application would use.

Query Patterns Demonstrated:
    1. ZOOM IN:  dhamma.downstream[] -> find expanded sub-lists
    2. ZOOM OUT: list.upstream_from[] -> find parent dhammas
    3. FRACTAL PATH: Recursive walk from a dhamma to root lists
    4. CROSS-REFS: dhamma.cross_references[] -> related concepts
    5. ORPHAN ROOTS: Lists with no upstream (entry points)
    6. FULL TREE: Recursive depth-first traversal

Usage:
    python query_examples.py              # Run all examples
    python query_examples.py zoom-in      # Run specific example
    python query_examples.py --list       # List available examples
"""

import argparse
import os
import sys

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "buddhist_dhammas")


def get_db():
    """Connect to MongoDB and return the database handle."""
    client = MongoClient(MONGO_URI)
    return client[MONGO_DB]


# ---------------------------------------------------------------------------
# Example 1: Zoom In
# ---------------------------------------------------------------------------

def example_zoom_in(db) -> None:
    """ZOOM IN: Start from a dhamma and find what it expands into.

    This is the core fractal navigation pattern. When a user clicks on
    "Right Concentration" in the UI, we look at its downstream[] array
    to find sub-lists they can explore deeper.

    Query chain:
        dhamma (by slug) -> downstream[].ref_id -> list doc -> list.children[]
    """
    print("\n" + "=" * 60)
    print("  ZOOM IN: Right Concentration -> What's inside?")
    print("=" * 60)

    # Find the dhamma we want to zoom into
    dhamma = db.dhammas.find_one({"slug": "right-concentration"})
    if not dhamma:
        print("  (dhamma 'right-concentration' not found — try seeding first)")
        return

    print(f"\n  Starting point: {dhamma['name']} ({dhamma['pali_name']})")
    print(f"  Essay preview: {dhamma.get('essay', '')[:100]}...")

    downstream = dhamma.get("downstream", [])
    if not downstream:
        print("  No downstream expansions found.")
        return

    for ref in downstream:
        if ref["ref_type"] == "list":
            sub_list = db.lists.find_one({"_id": ref["ref_id"]})
            if sub_list:
                print(f"\n  Expands into: {sub_list['name']} ({sub_list['pali_name']})")
                print(f"  Relationship: {ref.get('relationship_note', '')}")
                print(f"  Contains {sub_list['item_count']} items:")

                # Fetch the children dhammas
                children = db.dhammas.find(
                    {"_id": {"$in": sub_list.get("children", [])}}
                ).sort("position_in_list", 1)

                for child in children:
                    print(f"    {child['position_in_list']}. {child['name']} ({child['pali_name']})")


# ---------------------------------------------------------------------------
# Example 2: Zoom Out
# ---------------------------------------------------------------------------

def example_zoom_out(db) -> None:
    """ZOOM OUT: Start from a sub-list and find which dhamma leads to it.

    This is the reverse of zoom-in. The UI might show a breadcrumb trail:
    "You reached Five Hindrances by zooming into Right Concentration."

    Query chain:
        list (by slug) -> upstream_from[].ref_id -> parent dhamma
    """
    print("\n" + "=" * 60)
    print("  ZOOM OUT: Five Hindrances -> Where did this come from?")
    print("=" * 60)

    lst = db.lists.find_one({"slug": "five-hindrances"})
    if not lst:
        print("  (list 'five-hindrances' not found)")
        return

    print(f"\n  Current list: {lst['name']} ({lst['pali_name']})")

    upstream = lst.get("upstream_from", [])
    if not upstream:
        print("  This is a ROOT list — no upstream parent.")
        return

    for ref in upstream:
        if ref["ref_type"] == "dhamma":
            parent = db.dhammas.find_one({"_id": ref["ref_id"]})
            if parent:
                print(f"  Reached from: {parent['name']} ({parent['pali_name']})")
                print(f"  Relationship: {ref.get('relationship_note', '')}")

                # Show the parent's own context
                parent_list = db.lists.find_one({"_id": parent.get("parent_list_id")})
                if parent_list:
                    print(f"  Which belongs to: {parent_list['name']}")


# ---------------------------------------------------------------------------
# Example 3: Fractal Path (Walk to Root)
# ---------------------------------------------------------------------------

def example_fractal_path(db) -> None:
    """FRACTAL PATH: Walk upstream recursively from a deep dhamma to the root.

    This builds the full "breadcrumb trail" showing how any teaching connects
    back to the Four Noble Truths. It's the fractal zoom-out all the way.

    Algorithm:
        1. Start with a dhamma
        2. Find its parent list
        3. Check if that list has upstream_from[]
        4. If yes, go to the upstream dhamma and repeat from step 2
        5. If no, we've reached a root list
    """
    print("\n" + "=" * 60)
    print("  FRACTAL PATH: Trace from a leaf to the root")
    print("=" * 60)

    # Start deep in the tree — pick any expansion dhamma
    start = db.dhammas.find_one({"slug": "sensual-desire"})
    if not start:
        # Try another dhamma
        start = db.dhammas.find_one({"downstream.0": {"$exists": False}})
    if not start:
        print("  (no suitable starting dhamma found)")
        return

    print(f"\n  Starting from: {start['name']} ({start['pali_name']})")

    path = [f"{start['name']}"]
    current_list_id = start.get("parent_list_id")
    visited = set()  # Prevent infinite loops

    while current_list_id and current_list_id not in visited:
        visited.add(current_list_id)
        lst = db.lists.find_one({"_id": current_list_id})
        if not lst:
            break

        path.append(f"[{lst['name']}]")

        # Check for upstream parent dhamma
        upstream = lst.get("upstream_from", [])
        if not upstream:
            break  # Reached a root list

        # Follow the first upstream ref
        ref = upstream[0]
        if ref["ref_type"] == "dhamma":
            parent_dhamma = db.dhammas.find_one({"_id": ref["ref_id"]})
            if parent_dhamma:
                path.append(f"{parent_dhamma['name']}")
                current_list_id = parent_dhamma.get("parent_list_id")
            else:
                break
        else:
            break

    print("\n  Path (leaf → root):")
    for i, step in enumerate(path):
        indent = "    " + "  " * i
        arrow = "└─ " if i > 0 else ""
        print(f"{indent}{arrow}{step}")


# ---------------------------------------------------------------------------
# Example 4: Cross-References
# ---------------------------------------------------------------------------

def example_cross_refs(db) -> None:
    """CROSS-REFERENCES: Find where the same concept appears in different lists.

    Buddhist concepts often appear in multiple teaching frameworks. For example,
    "Upekkha" (equanimity) is both a Brahma Vihara and a Factor of Awakening.
    Cross-references let the UI show "See also..." connections.
    """
    print("\n" + "=" * 60)
    print("  CROSS-REFERENCES: Concepts that appear in multiple lists")
    print("=" * 60)

    # Find dhammas that have cross-references
    with_xrefs = db.dhammas.find(
        {"cross_references.0": {"$exists": True}}
    ).limit(5)

    found_any = False
    for d in with_xrefs:
        found_any = True
        print(f"\n  {d['name']} ({d['pali_name']})")
        parent = db.lists.find_one({"_id": d.get("parent_list_id")})
        if parent:
            print(f"    Primary list: {parent['name']}")

        for ref in d.get("cross_references", []):
            related = db.dhammas.find_one({"_id": ref["ref_id"]})
            if related:
                rel_parent = db.lists.find_one({"_id": related.get("parent_list_id")})
                rel_list_name = rel_parent["name"] if rel_parent else "?"
                print(
                    f"    Also in: {rel_list_name} as '{related['name']}'"
                    f"  — {ref.get('note', '')}"
                )

    if not found_any:
        print("  No cross-references found. This may indicate parsing needs tuning.")


# ---------------------------------------------------------------------------
# Example 5: Root Lists (Orphans)
# ---------------------------------------------------------------------------

def example_root_lists(db) -> None:
    """ROOT LISTS: Find all lists with no upstream parent.

    These are the entry points to the knowledge graph — the "top level"
    that a user sees when they first open the app. Usually includes the
    Four Noble Truths, Three Jewels, Three Marks of Existence, etc.
    """
    print("\n" + "=" * 60)
    print("  ROOT LISTS: Entry points to the knowledge graph")
    print("=" * 60)

    roots = db.lists.find(
        {"$or": [{"upstream_from": {"$size": 0}}, {"upstream_from": {"$exists": False}}]}
    ).sort("name", 1)

    print()
    for lst in roots:
        child_count = len(lst.get("children", []))
        print(f"  {lst['name']:45s} ({lst['pali_name']})")
        print(f"    {child_count} children, slug: {lst['slug']}")


# ---------------------------------------------------------------------------
# Example 6: Full Tree Traversal
# ---------------------------------------------------------------------------

def example_full_tree(db) -> None:
    """FULL TREE: Recursive depth-first traversal from a root list.

    Shows the complete fractal structure starting from one root list.
    This is what powers a tree-view or outline display in the UI.
    """
    print("\n" + "=" * 60)
    print("  FULL TREE: Depth-first traversal from Four Noble Truths")
    print("=" * 60)

    root = db.lists.find_one({"slug": "four-noble-truths"})
    if not root:
        print("  (list 'four-noble-truths' not found)")
        return

    visited = set()
    max_depth = 3  # Limit depth to keep output readable

    def print_tree(list_doc, depth=0):
        """Recursively print a list and its children."""
        if list_doc["_id"] in visited or depth > max_depth:
            if depth > max_depth:
                print(f"{'    ' * (depth + 1)}... (truncated at depth {max_depth})")
            return
        visited.add(list_doc["_id"])

        indent = "    " * depth
        print(f"{indent}[{list_doc['name']}] ({list_doc.get('item_count', '?')} items)")

        # Get children dhammas in order
        children = list(
            db.dhammas.find({"_id": {"$in": list_doc.get("children", [])}}).sort(
                "position_in_list", 1
            )
        )

        for child in children:
            print(f"{indent}  └─ {child['name']} ({child['pali_name']})")

            # Check if this dhamma has downstream lists (fractal zoom)
            for ref in child.get("downstream", []):
                if ref["ref_type"] == "list":
                    sub_list = db.lists.find_one({"_id": ref["ref_id"]})
                    if sub_list:
                        print_tree(sub_list, depth + 2)

    print()
    print_tree(root)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

EXAMPLES = {
    "zoom-in": ("Zoom into a dhamma's downstream lists", example_zoom_in),
    "zoom-out": ("Zoom out to find a list's upstream parent", example_zoom_out),
    "fractal-path": ("Walk from a leaf dhamma to the root", example_fractal_path),
    "cross-refs": ("Find cross-referenced concepts", example_cross_refs),
    "root-lists": ("Show all root entry points", example_root_lists),
    "full-tree": ("Depth-first tree traversal", example_full_tree),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demonstrate query patterns for Buddhist Dhammas graph"
    )
    parser.add_argument(
        "example",
        nargs="?",
        choices=list(EXAMPLES.keys()),
        help="Run a specific example (default: all)",
    )
    parser.add_argument(
        "--list", action="store_true", help="List available examples"
    )
    args = parser.parse_args()

    if args.list:
        print("\nAvailable examples:")
        for name, (desc, _) in EXAMPLES.items():
            print(f"  {name:20s} {desc}")
        return

    db = get_db()

    if args.example:
        _, func = EXAMPLES[args.example]
        func(db)
    else:
        print("\n" + "#" * 60)
        print("  BUDDHIST DHAMMAS — QUERY EXAMPLES")
        print("#" * 60)
        for name, (desc, func) in EXAMPLES.items():
            func(db)

    print()


if __name__ == "__main__":
    main()
