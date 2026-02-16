#!/usr/bin/env python3
"""
validate_db.py — Verify data integrity of the Buddhist Dhammas database.

Runs a comprehensive set of checks against the seeded MongoDB database to
ensure all references are valid and the knowledge graph is consistent.

Checks performed:
    1. All ObjectId references point to existing documents
    2. Parent-child relationships are valid (bidirectional)
    3. No circular dependencies in upstream-downstream chains
    4. Containment vs zoom distinction maintained (critical rule)
    5. All dhammas have essays loaded
    6. Item counts match actual children arrays
    7. All slugs are unique
    8. No orphan dhammas (every dhamma has a parent list)

Exit codes:
    0 = All checks pass
    1 = One or more checks failed

Usage:
    python validate_db.py           # Run all checks
    python validate_db.py --verbose  # Show details for passing checks too
"""

import argparse
import logging
import os
import sys

from pymongo import MongoClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "buddhist_dhammas")


class ValidationResult:
    """Accumulates pass/fail results for all validation checks."""

    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        """Record a check result."""
        self.checks.append((name, passed, detail))
        status = "PASS" if passed else "FAIL"
        icon = "\u2705" if passed else "\u274c"
        msg = f"  {icon} {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed, _ in self.checks)

    def summary(self) -> None:
        passed = sum(1 for _, p, _ in self.checks if p)
        total = len(self.checks)
        print(f"\n{'=' * 50}")
        if self.all_passed:
            print(f"  ALL {total} CHECKS PASSED")
        else:
            print(f"  {passed}/{total} CHECKS PASSED")
            print("  Failed checks:")
            for name, p, detail in self.checks:
                if not p:
                    print(f"    - {name}: {detail}")
        print(f"{'=' * 50}")


def validate(verbose: bool = False) -> bool:
    """Run all validation checks against the database.

    Args:
        verbose: If True, show extra detail for passing checks.

    Returns:
        True if all checks pass, False otherwise.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    result = ValidationResult()

    # Load all docs into memory (small dataset, ~200 docs total)
    all_lists = list(db.lists.find())
    all_dhammas = list(db.dhammas.find())

    list_ids = {doc["_id"] for doc in all_lists}
    dhamma_ids = {doc["_id"] for doc in all_dhammas}
    all_ids = list_ids | dhamma_ids

    list_by_id = {doc["_id"]: doc for doc in all_lists}
    dhamma_by_id = {doc["_id"]: doc for doc in all_dhammas}

    print(f"\nValidating database: {len(all_lists)} lists, {len(all_dhammas)} dhammas\n")

    # --- Check 1: Database not empty ---
    result.add(
        "Database populated",
        len(all_lists) > 0 and len(all_dhammas) > 0,
        f"{len(all_lists)} lists, {len(all_dhammas)} dhammas",
    )

    # --- Check 2: All list.children[] point to existing dhammas ---
    broken_children = []
    for lst in all_lists:
        for child_id in lst.get("children", []):
            if child_id not in dhamma_ids:
                broken_children.append((lst["slug"], str(child_id)))
    result.add(
        "List children refs valid",
        len(broken_children) == 0,
        f"{len(broken_children)} broken refs" if broken_children else "",
    )

    # --- Check 3: All dhamma.parent_list_id points to existing list ---
    orphan_dhammas = []
    for d in all_dhammas:
        parent_id = d.get("parent_list_id")
        if parent_id is None or parent_id not in list_ids:
            orphan_dhammas.append(d["slug"])
    result.add(
        "All dhammas have valid parent list",
        len(orphan_dhammas) == 0,
        f"{len(orphan_dhammas)} orphans: {orphan_dhammas[:5]}" if orphan_dhammas else "",
    )

    # --- Check 4: Bidirectional parent-child consistency ---
    # Every dhamma's parent_list_id should have that dhamma in its children[]
    inconsistent = []
    for d in all_dhammas:
        parent_id = d.get("parent_list_id")
        if parent_id and parent_id in list_by_id:
            parent = list_by_id[parent_id]
            if d["_id"] not in parent.get("children", []):
                inconsistent.append(d["slug"])
    result.add(
        "Parent-child bidirectional",
        len(inconsistent) == 0,
        f"{len(inconsistent)} inconsistent" if inconsistent else "",
    )

    # --- Check 5: All downstream refs point to existing docs ---
    broken_downstream = []
    for d in all_dhammas:
        for ref in d.get("downstream", []):
            ref_id = ref.get("ref_id")
            if ref_id not in all_ids:
                broken_downstream.append((d["slug"], str(ref_id)))
    result.add(
        "Downstream refs valid",
        len(broken_downstream) == 0,
        f"{len(broken_downstream)} broken" if broken_downstream else "",
    )

    # --- Check 6: All upstream_from refs point to existing docs ---
    broken_upstream = []
    for lst in all_lists:
        for ref in lst.get("upstream_from", []):
            ref_id = ref.get("ref_id")
            if ref_id not in all_ids:
                broken_upstream.append((lst["slug"], str(ref_id)))
    result.add(
        "Upstream refs valid",
        len(broken_upstream) == 0,
        f"{len(broken_upstream)} broken" if broken_upstream else "",
    )

    # --- Check 7: All cross_references point to existing dhammas ---
    broken_xrefs = []
    for d in all_dhammas:
        for ref in d.get("cross_references", []):
            ref_id = ref.get("ref_id")
            if ref_id not in dhamma_ids:
                broken_xrefs.append((d["slug"], str(ref_id)))
    result.add(
        "Cross-reference refs valid",
        len(broken_xrefs) == 0,
        f"{len(broken_xrefs)} broken" if broken_xrefs else "",
    )

    # --- Check 8: Critical Rule — children are NOT downstream from own parent ---
    # Containment (parent-child) is different from fractal zoom (downstream).
    # A dhamma should never have a downstream ref pointing to its own parent list.
    containment_violations = []
    for d in all_dhammas:
        parent_id = d.get("parent_list_id")
        for ref in d.get("downstream", []):
            if ref.get("ref_id") == parent_id and ref.get("ref_type") == "list":
                containment_violations.append(d["slug"])
    result.add(
        "Containment ≠ zoom (critical rule)",
        len(containment_violations) == 0,
        f"{len(containment_violations)} violations" if containment_violations else "",
    )

    # --- Check 9: No circular dependencies in downstream chains ---
    # Walk downstream from each dhamma and check for cycles.
    cycles_found = []

    def has_cycle(start_id, visited=None):
        """DFS to detect cycles in downstream relationships."""
        if visited is None:
            visited = set()
        if start_id in visited:
            return True
        visited.add(start_id)

        doc = dhamma_by_id.get(start_id)
        if not doc:
            return False
        for ref in doc.get("downstream", []):
            ref_id = ref.get("ref_id")
            if ref.get("ref_type") == "list" and ref_id in list_by_id:
                # Follow into list's children
                lst = list_by_id[ref_id]
                for child_id in lst.get("children", []):
                    if has_cycle(child_id, visited.copy()):
                        return True
        return False

    for d in all_dhammas:
        if has_cycle(d["_id"]):
            cycles_found.append(d["slug"])
    result.add(
        "No circular dependencies",
        len(cycles_found) == 0,
        f"{len(cycles_found)} cycles" if cycles_found else "",
    )

    # --- Check 10: item_count matches actual children length ---
    count_mismatches = []
    for lst in all_lists:
        actual = len(lst.get("children", []))
        declared = lst.get("item_count", 0)
        if actual != declared:
            count_mismatches.append(
                f"{lst['slug']}: declared={declared}, actual={actual}"
            )
    result.add(
        "Item counts accurate",
        len(count_mismatches) == 0,
        "; ".join(count_mismatches[:3]) if count_mismatches else "",
    )

    # --- Check 11: All slugs are unique ---
    list_slugs = [doc["slug"] for doc in all_lists]
    dhamma_slugs = [doc["slug"] for doc in all_dhammas]
    dup_list = len(list_slugs) != len(set(list_slugs))
    dup_dhamma = len(dhamma_slugs) != len(set(dhamma_slugs))
    result.add(
        "All slugs unique",
        not dup_list and not dup_dhamma,
        f"list dupes={dup_list}, dhamma dupes={dup_dhamma}"
        if dup_list or dup_dhamma
        else "",
    )

    # --- Check 12: Essay coverage ---
    with_essays = sum(1 for d in all_dhammas if d.get("essay"))
    total = len(all_dhammas)
    coverage = (with_essays / total * 100) if total else 0
    result.add(
        "Essay coverage",
        with_essays == total,
        f"{with_essays}/{total} ({coverage:.0f}%)",
    )

    # --- Summary ---
    result.summary()
    client.close()
    return result.all_passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Buddhist Dhammas database")
    parser.add_argument("--verbose", action="store_true", help="Show extra detail")
    args = parser.parse_args()

    passed = validate(verbose=args.verbose)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
