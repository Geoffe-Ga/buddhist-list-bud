#!/usr/bin/env python3
"""
seed_db.py — Parse the Buddhist dhammas spreadsheet and seed MongoDB.

This is the core data pipeline for the fractal knowledge graph. It reads the
Excel spreadsheet, extracts lists and dhammas, wires up all three relationship
types (parent-child, upstream-downstream, cross-references), and inserts
everything into MongoDB.

IDEMPOTENT: Safe to re-run. Drops and recreates the database each time,
but preserves any generated essays stored in data/essays/.

Parsing Strategy:
    1. Parse column headers to create the 9 major lists
    2. Walk rows to extract dhammas and assign them to parent lists
    3. Use Notes column to identify sub-lists (grouped expansions)
    4. Use column co-occurrence to build downstream relationships
    5. Parse Sheet 2 for foundational/cross-cutting lists
    6. Convert slug-based references to ObjectIds after all inserts
    7. Load essays from data/essays/{slug}.md if they exist

Key Concepts:
    - "List" = a named group of teachings (e.g., Noble Eightfold Path)
    - "Dhamma" = an individual teaching (e.g., Right Concentration)
    - "Downstream" = a dhamma expands into a sub-list (fractal zoom IN)
    - "Upstream" = a list is reached by zooming into a parent dhamma
    - "Cross-reference" = same concept appearing in different contexts
"""

import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "buddhist_dhammas")
SPREADSHEET = Path(__file__).parent / "buddhist_list_bud_content_v1.xlsx"
ESSAYS_DIR = Path(__file__).parent / "data" / "essays"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Turn a name into a URL-friendly slug.

    Examples:
        >>> slugify("Right Concentration (Samma Samadhi)")
        'right-concentration'
        >>> slugify("1. There is Suffering")
        'there-is-suffering'
    """
    # Remove parenthetical Pali names
    text = re.sub(r"\(.*?\)", "", text)
    # Remove leading numbers like "1. "
    text = re.sub(r"^\d+\.\s*", "", text)
    # Remove special characters, lowercase, collapse whitespace
    text = re.sub(r"[^a-z0-9\s-]", "", text.lower().strip())
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def parse_header(header_text: str) -> tuple[str, str]:
    """Extract English name and Pali name from a column header.

    Headers look like "Four Noble Truths\\n(Cattari Ariya-saccani)".
    Returns (english_name, pali_name).
    """
    if not isinstance(header_text, str):
        return str(header_text), ""
    parts = header_text.replace("\n", "|").split("|")
    english = parts[0].strip()
    pali = ""
    if len(parts) > 1:
        pali = parts[1].strip().strip("()")
    return english, pali


def extract_pali_from_name(name: str) -> tuple[str, str]:
    """Split 'Right View (Samma Ditthi)' into name and pali.

    Returns (clean_name, pali_name). If no parenthetical, pali is empty.
    """
    match = re.search(r"\(([^)]+)\)\s*$", name)
    if match:
        pali = match.group(1)
        clean = name[: match.start()].strip()
        return clean, pali
    return name.strip(), ""


def strip_number_prefix(text: str) -> str:
    """Remove leading '1. ' style prefixes from dhamma names."""
    return re.sub(r"^\d+\.\s*", "", text).strip()


def load_essay(slug: str) -> str:
    """Load a pre-generated essay from data/essays/{slug}.md.

    Returns empty string if the essay file doesn't exist yet.
    This lets seed_db.py run before generate_essays.py — essays
    get populated on a later run.
    """
    path = ESSAYS_DIR / f"{slug}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


# ---------------------------------------------------------------------------
# Spreadsheet Parsing
# ---------------------------------------------------------------------------


def parse_nested_lists_sheet(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Parse the 'Nested Lists' sheet into lists and dhammas.

    The sheet has 9 main columns (0-8) representing parent lists,
    a 'Sub-lists / Expansions' column (9) for downstream items,
    a Pali Term column (10), and a Notes column (11).

    Parsing happens in three passes:
        Pass 1: Create lists from column headers, extract all dhammas
        Pass 2: Detect sub-list groups from Notes and assign expansion items
        Pass 3: Detect implicit downstream relationships from column co-occurrence
                 (e.g., Right Concentration rows also have Five Hindrances items)

    Returns:
        (lists, dhammas) — each as a list of dicts with slug-based refs.
    """
    lists = {}  # slug -> list dict
    dhammas = {}  # slug -> dhamma dict

    # --- Step 1: Create the 9 major lists from column headers ---
    header_row = df.iloc[0]
    main_list_columns = {}  # col_index -> list_slug

    for col_idx in range(9):
        header_val = header_row.iloc[col_idx]
        if pd.isna(header_val):
            continue
        name, pali = parse_header(str(header_val))
        slug = slugify(name)
        main_list_columns[col_idx] = slug
        lists[slug] = {
            "name": name,
            "pali_name": pali,
            "slug": slug,
            "description": "",
            "children": [],
            "upstream_from": [],
            "tradition": "Theravada",
            "source_texts": [],
            "item_count": 0,
        }

    log.info("Found %d major lists from column headers", len(lists))

    # --- Step 2: Walk data rows to extract dhammas and sub-lists ---
    # Track which sub-list group each row belongs to (from Notes column).
    # When Notes mentions a sub-list name like "Five Aggregates (Pañca-khandha)",
    # we create that as a new list and assign subsequent rows' col-9 items to it.

    current_sublist_slug = None
    current_sublist_parent_dhamma_slug = None

    # Known sub-list patterns: regex in Notes that triggers sub-list creation.
    # Matches "Four Stages of Enlightenment", "Five Faculties & Five Powers", etc.
    # Two variants: with Pali in parens, or with a dash/em-dash description.
    sublist_with_pali = re.compile(
        r"^((?:Three|Four|Five|Six|Seven|Eight|Nine|Ten|Twelve|Thirty.?seven)"
        r"\s+[\w\s&/]+?)\s*\(([^)]+)\)"
    )
    sublist_without_pali = re.compile(
        r"^((?:Three|Four|Five|Six|Seven|Eight|Nine|Ten|Twelve|Thirty.?seven)"
        r"\s+[\w\s&/]+?)\s*[\u2014—-]\s"
    )

    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx]

        # Get the expansion item, pali term, and notes for this row
        expansion = row.iloc[9] if not pd.isna(row.iloc[9]) else None
        pali_term = str(row.iloc[10]).strip() if not pd.isna(row.iloc[10]) else ""
        notes = str(row.iloc[11]).strip() if not pd.isna(row.iloc[11]) else ""

        # --- Identify which main list columns have values this row ---
        deepest_col = None
        for col_idx in range(8, -1, -1):
            if col_idx in main_list_columns and not pd.isna(row.iloc[col_idx]):
                deepest_col = col_idx
                break

        # --- Handle main-column dhammas (columns 0-8) ---
        row_dhamma_slugs = {}  # col_idx -> dhamma_slug for this row
        for col_idx in range(9):
            val = row.iloc[col_idx]
            if pd.isna(val) or col_idx not in main_list_columns:
                continue
            val = str(val).strip()
            if not val:
                continue

            dhamma_name, dhamma_pali = extract_pali_from_name(val)
            dhamma_name_clean = strip_number_prefix(dhamma_name)
            dhamma_slug = slugify(dhamma_name_clean)
            row_dhamma_slugs[col_idx] = dhamma_slug
            parent_list_slug = main_list_columns[col_idx]

            if dhamma_slug not in dhammas:
                dhammas[dhamma_slug] = {
                    "name": dhamma_name_clean,
                    "pali_name": dhamma_pali,
                    "slug": dhamma_slug,
                    "parent_list_slug": parent_list_slug,
                    "position_in_list": 0,
                    "essay": "",
                    "downstream": [],
                    "upstream_from": [],
                    "cross_references": [],
                    "tags": [],
                    "notes": "",
                }
                if dhamma_slug not in lists[parent_list_slug]["children"]:
                    lists[parent_list_slug]["children"].append(dhamma_slug)

        # --- Detect sub-list groups from Notes column ---
        # Match "Five Aggregates (Pañca-khandha)" or
        # "Four Stages of Enlightenment — breaks..."
        sublist_name = None
        sublist_pali = ""

        match_with_pali = sublist_with_pali.match(notes)
        match_without_pali = sublist_without_pali.match(notes)

        if match_with_pali and expansion:
            sublist_name = match_with_pali.group(1).strip()
            sublist_pali = match_with_pali.group(2).strip()
        elif match_without_pali and expansion:
            sublist_name = match_without_pali.group(1).strip()

        if sublist_name:
            sublist_slug = slugify(sublist_name)
            if sublist_slug not in lists:
                lists[sublist_slug] = {
                    "name": sublist_name,
                    "pali_name": sublist_pali,
                    "slug": sublist_slug,
                    "description": "",
                    "children": [],
                    "upstream_from": [],
                    "tradition": "Theravada",
                    "source_texts": [],
                    "item_count": 0,
                }
                log.info(
                    "  Created sub-list: %s (%s)",
                    sublist_name,
                    sublist_pali or "no Pali",
                )

            current_sublist_slug = sublist_slug

            # The parent dhamma is the deepest main-column dhamma on this row
            if deepest_col is not None and deepest_col in row_dhamma_slugs:
                current_sublist_parent_dhamma_slug = row_dhamma_slugs[deepest_col]
                _wire_downstream(
                    dhammas,
                    lists,
                    current_sublist_parent_dhamma_slug,
                    sublist_slug,
                    sublist_name,
                )

        # --- Handle expansion items (column 9) ---
        if expansion:
            expansion = str(expansion).strip()
            exp_name_raw, exp_pali_from_name = extract_pali_from_name(expansion)
            exp_name = strip_number_prefix(exp_name_raw)
            exp_slug = slugify(exp_name)
            exp_pali = pali_term if pali_term else exp_pali_from_name

            target_list_slug = current_sublist_slug

            # If no active sub-list, create an IMPLICIT one rather than
            # polluting the main column's list. For example, rows 1-3 have
            # expansion items (types of suffering) under "There is Suffering"
            # but no named sub-list in Notes. We create one automatically.
            if not target_list_slug and deepest_col is not None:
                parent_slug = row_dhamma_slugs.get(deepest_col)
                if parent_slug and parent_slug in dhammas:
                    parent_name = dhammas[parent_slug]["name"]
                    implicit_slug = f"{parent_slug}-aspects"
                    if implicit_slug not in lists:
                        implicit_name = f"Aspects of {parent_name}"
                        lists[implicit_slug] = {
                            "name": implicit_name,
                            "pali_name": "",
                            "slug": implicit_slug,
                            "description": f"Sub-teachings expanding on {parent_name}",
                            "children": [],
                            "upstream_from": [],
                            "tradition": "Theravada",
                            "source_texts": [],
                            "item_count": 0,
                        }
                        log.info("  Created implicit sub-list: %s", implicit_name)
                        _wire_downstream(
                            dhammas,
                            lists,
                            parent_slug,
                            implicit_slug,
                            implicit_name,
                        )
                    target_list_slug = implicit_slug
                    current_sublist_slug = implicit_slug
                    current_sublist_parent_dhamma_slug = parent_slug

            if target_list_slug and target_list_slug in lists:
                if exp_slug not in dhammas:
                    dhammas[exp_slug] = {
                        "name": exp_name,
                        "pali_name": exp_pali,
                        "slug": exp_slug,
                        "parent_list_slug": target_list_slug,
                        "position_in_list": 0,
                        "essay": "",
                        "downstream": [],
                        "upstream_from": [],
                        "cross_references": [],
                        "tags": [],
                        "notes": notes,
                    }
                elif not dhammas[exp_slug]["notes"] and notes:
                    dhammas[exp_slug]["notes"] = notes

                if exp_slug not in lists[target_list_slug]["children"]:
                    lists[target_list_slug]["children"].append(exp_slug)

                if pali_term and not dhammas[exp_slug]["pali_name"]:
                    dhammas[exp_slug]["pali_name"] = pali_term
        else:
            # No expansion on this row — reset sub-list tracking if there's
            # also no active sub-list context continuing from a previous row.
            # Only reset when we see a row WITHOUT expansion, which signals
            # we've moved past the sub-list group.
            if current_sublist_slug and not expansion:
                # Check if the next row also has no expansion — if so, we've
                # left the sub-list context. But don't reset yet; wait for the
                # next row to confirm.
                pass

        # --- Assign Pali/notes to deepest main-column dhamma ---
        if deepest_col is not None and deepest_col in row_dhamma_slugs:
            d_slug = row_dhamma_slugs[deepest_col]
            if d_slug in dhammas:
                if pali_term and not dhammas[d_slug]["pali_name"]:
                    dhammas[d_slug]["pali_name"] = pali_term
                if notes and not dhammas[d_slug]["notes"]:
                    dhammas[d_slug]["notes"] = notes

        # --- Reset sub-list tracking ---
        # Only reset when a different sub-list is detected (handled above)
        # or when we hit a row with no expansion AND the deepest column
        # dhamma changed from the sub-list's parent.
        # Check if the deepest dhamma on this row is different from
        # the sub-list's parent — if so, we've left that context
        if (
            not expansion
            and current_sublist_slug
            and deepest_col is not None
            and deepest_col in row_dhamma_slugs
        ):
            new_parent = row_dhamma_slugs[deepest_col]
            if new_parent != current_sublist_parent_dhamma_slug:
                current_sublist_slug = None
                current_sublist_parent_dhamma_slug = None

    # --- Step 3: Detect implicit downstream from column co-occurrence ---
    # When a dhamma in column X co-occurs with items in a deeper column Y,
    # that's a downstream relationship: dhamma X -> list Y.
    # E.g., "Right Concentration" in col 2 co-occurs with Five Hindrances
    # items in col 5, so Right Concentration -> Five Hindrances list.
    _detect_column_downstream(df, main_list_columns, lists, dhammas)

    return list(lists.values()), list(dhammas.values())


def _wire_downstream(
    dhammas: dict,
    lists: dict,
    parent_dhamma_slug: str,
    list_slug: str,
    list_name: str,
) -> None:
    """Wire up a downstream relationship: parent dhamma -> sub-list.

    Also wires the reverse upstream: sub-list -> parent dhamma.
    Helper to avoid repeating this logic in multiple places.
    """
    if parent_dhamma_slug not in dhammas or list_slug not in lists:
        return

    parent_d = dhammas[parent_dhamma_slug]
    downstream_entry = {
        "ref_slug": list_slug,
        "ref_type": "list",
        "relationship_note": f"Expands into {list_name}",
    }
    if downstream_entry not in parent_d["downstream"]:
        parent_d["downstream"].append(downstream_entry)

    upstream_entry = {
        "ref_slug": parent_dhamma_slug,
        "ref_type": "dhamma",
        "relationship_note": f"Zooms in from {parent_d['name']}",
    }
    if upstream_entry not in lists[list_slug]["upstream_from"]:
        lists[list_slug]["upstream_from"].append(upstream_entry)


def _detect_column_downstream(
    df: pd.DataFrame,
    main_list_columns: dict[int, str],
    lists: dict[str, dict],
    dhammas: dict[str, dict],
) -> None:
    """Detect implicit downstream relationships from column co-occurrence.

    When a dhamma in column X appears on the same row as items in a deeper
    column Y (Y > X), and the column Y items are unique to that dhamma's rows,
    then dhamma X has a downstream relationship to list Y.

    For example:
        - Right Concentration (col 2) rows also have Five Hindrances items (col 5)
        - Right Mindfulness (col 2) rows also have Four Foundations items (col 6)
        - There is a Path (col 0) rows have Noble Eightfold Path items (col 2)

    This creates the fractal zoom relationships that the column structure implies.
    """
    # Build a map: for each main-column dhamma, which deeper columns have items
    # dhamma_slug -> set of deeper column indices that appear on its rows
    dhamma_deeper_cols: dict[str, dict[int, set]] = {}

    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx]

        # Find all active columns on this row
        active_cols = {}
        for col_idx in sorted(main_list_columns.keys()):
            val = row.iloc[col_idx]
            if not pd.isna(val):
                name_raw, _ = extract_pali_from_name(str(val).strip())
                slug = slugify(strip_number_prefix(name_raw))
                active_cols[col_idx] = slug

        # For each dhamma, record which deeper columns co-occur
        for col_idx, slug in active_cols.items():
            if slug not in dhamma_deeper_cols:
                dhamma_deeper_cols[slug] = {}
            for deeper_col, _deeper_slug in active_cols.items():
                if deeper_col > col_idx:
                    dhamma_deeper_cols[slug].setdefault(deeper_col, set()).add(row_idx)

    # Now wire downstream for each dhamma -> deeper list where the deeper list
    # has items that ONLY appear with this dhamma (not shared with other dhammas
    # in the same column).
    for dhamma_slug, deeper_map in dhamma_deeper_cols.items():
        if dhamma_slug not in dhammas:
            continue
        for deeper_col, _row_set in deeper_map.items():
            if deeper_col not in main_list_columns:
                continue
            list_slug = main_list_columns[deeper_col]
            if list_slug not in lists:
                continue

            # Skip if the dhamma IS in the deeper list (that's containment, not zoom)
            if dhamma_slug in lists[list_slug]["children"]:
                continue

            # Skip column 0 -> column 1 (Four Noble Truths -> Three Trainings)
            # because Three Trainings is a grouping mechanism, not a true downstream.
            # The real downstream is Noble Truths -> Eightfold Path.
            # We keep col 0 -> col 2+ though.

            _wire_downstream(
                dhammas,
                lists,
                dhamma_slug,
                list_slug,
                lists[list_slug]["name"],
            )

    log.info("Detected implicit downstream relationships from column co-occurrence")


def parse_foundations_sheet(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Parse the 'Foundations & Cross-Cutting' sheet.

    This sheet has a simpler structure: List name, Item, Pali Term, Notes.
    Lists here include Three Jewels, Three Marks of Existence, Six Sense Bases,
    and the 37 Factors of Enlightenment meta-list.

    Returns:
        (lists, dhammas) — with slug-based references.
    """
    lists = {}
    dhammas = []

    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx]
        list_name = row.iloc[0] if not pd.isna(row.iloc[0]) else None
        item_name = row.iloc[1] if not pd.isna(row.iloc[1]) else None
        pali_term = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ""
        notes = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else ""

        if not list_name or not item_name:
            continue

        list_name = str(list_name).strip()
        item_name = str(item_name).strip()

        # Extract Pali from list name like "Three Jewels (Ti-ratana)"
        list_clean, list_pali = extract_pali_from_name(list_name)
        list_slug = slugify(list_clean)

        if list_slug not in lists:
            lists[list_slug] = {
                "name": list_clean,
                "pali_name": list_pali,
                "slug": list_slug,
                "description": "",
                "children": [],
                "upstream_from": [],
                "tradition": "Theravada",
                "source_texts": [],
                "item_count": 0,
            }

        item_clean, item_pali = extract_pali_from_name(item_name)
        item_slug = slugify(item_clean)
        if not item_pali:
            item_pali = pali_term

        dhamma = {
            "name": item_clean,
            "pali_name": item_pali,
            "slug": item_slug,
            "parent_list_slug": list_slug,
            "position_in_list": 0,
            "essay": "",
            "downstream": [],
            "upstream_from": [],
            "cross_references": [],
            "tags": [],
            "notes": notes,
        }
        dhammas.append(dhamma)

        if item_slug not in lists[list_slug]["children"]:
            lists[list_slug]["children"].append(item_slug)

    return list(lists.values()), dhammas


# ---------------------------------------------------------------------------
# Cross-Reference Detection
# ---------------------------------------------------------------------------


def detect_cross_references(dhammas: list[dict]) -> None:
    """Find dhammas that share the same Pali term across different lists.

    When the same concept appears in multiple lists (e.g., "Upekkha" as both
    a Brahma Vihara and a Factor of Awakening), we link them as cross-references.
    This lets the UI show "this concept also appears in..." connections.

    Mutates dhammas in place by adding to their cross_references lists.
    """
    # Build a map of pali_term -> list of dhamma slugs
    pali_map: dict[str, list[str]] = {}
    dhamma_lookup = {d["slug"]: d for d in dhammas}

    for d in dhammas:
        pali = d["pali_name"].lower().strip()
        if not pali:
            continue
        # Normalize compound Pali terms
        # e.g., "Lobha (Raga/Tanha)" -> check each part
        for term in re.split(r"[/(),\s]+", pali):
            term = term.strip()
            if len(term) < 3:  # skip very short fragments
                continue
            pali_map.setdefault(term, []).append(d["slug"])

    cross_ref_count = 0
    for term, slugs in pali_map.items():
        unique_slugs = list(set(slugs))
        if len(unique_slugs) < 2:
            continue
        # Cross-reference each pair, but only if they're in different parent lists
        for i, slug_a in enumerate(unique_slugs):
            for slug_b in unique_slugs[i + 1 :]:
                da = dhamma_lookup.get(slug_a)
                db = dhamma_lookup.get(slug_b)
                if not da or not db:
                    continue
                if da["parent_list_slug"] == db["parent_list_slug"]:
                    continue  # Same list = not a cross-reference

                db_list = db["parent_list_slug"]
                da_list = da["parent_list_slug"]
                ref_a = {
                    "ref_slug": slug_b,
                    "ref_type": "dhamma",
                    "note": f"Shared Pali '{term}' — also in {db_list}",
                }
                ref_b = {
                    "ref_slug": slug_a,
                    "ref_type": "dhamma",
                    "note": f"Shared Pali '{term}' — also in {da_list}",
                }
                if ref_a not in da["cross_references"]:
                    da["cross_references"].append(ref_a)
                    cross_ref_count += 1
                if ref_b not in db["cross_references"]:
                    db["cross_references"].append(ref_b)
                    cross_ref_count += 1

    log.info("Detected %d cross-references via shared Pali terms", cross_ref_count)


# ---------------------------------------------------------------------------
# Position Assignment
# ---------------------------------------------------------------------------


def assign_positions(lists_data: list[dict], dhammas_data: list[dict]) -> None:
    """Assign position_in_list for each dhamma based on its order in the
    parent list's children array.

    Also sets item_count on each list.
    """
    dhamma_lookup = {d["slug"]: d for d in dhammas_data}
    for lst in lists_data:
        lst["item_count"] = len(lst["children"])
        for pos, child_slug in enumerate(lst["children"], start=1):
            if child_slug in dhamma_lookup:
                dhamma_lookup[child_slug]["position_in_list"] = pos


# ---------------------------------------------------------------------------
# MongoDB Insertion
# ---------------------------------------------------------------------------


def seed_database(lists_data: list[dict], dhammas_data: list[dict]) -> None:
    """Insert all lists and dhammas into MongoDB, then resolve slug refs to ObjectIds.

    This is where the slug -> ObjectId conversion happens. During parsing, all
    references use slugs (because we can't reference docs that don't exist yet).
    After inserting everything, we do a final pass to replace slugs with real
    MongoDB ObjectIds.

    Why this two-pass approach?
        MongoDB ObjectIds are generated on insert, but our data has circular
        references (list.children -> dhamma, dhamma.parent_list_id -> list).
        Slugs act as stable temporary IDs that work before any docs exist.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]

    # Drop existing collections for idempotency
    db.lists.drop()
    db.dhammas.drop()
    log.info("Dropped existing collections (idempotent reset)")

    # --- Load essays into dhammas before insert ---
    for d in dhammas_data:
        essay = load_essay(d["slug"])
        if essay:
            d["essay"] = essay

    # --- Insert lists ---
    # Store children as slugs for now; we'll convert after insert
    lists_to_insert = []
    for lst in lists_data:
        doc = {
            "name": lst["name"],
            "pali_name": lst["pali_name"],
            "slug": lst["slug"],
            "description": lst.get("description", ""),
            "children_slugs": lst["children"],  # temporary slug refs
            "children": [],  # will be filled with ObjectIds
            "upstream_from_slugs": lst.get("upstream_from", []),
            "upstream_from": [],
            "tradition": "Theravada",
            "source_texts": lst.get("source_texts", []),
            "item_count": lst.get("item_count", 0),
        }
        lists_to_insert.append(doc)

    if lists_to_insert:
        db.lists.insert_many(lists_to_insert)
    log.info("Inserted %d lists", len(lists_to_insert))

    # --- Insert dhammas ---
    dhammas_to_insert = []
    for d in dhammas_data:
        doc = {
            "name": d["name"],
            "pali_name": d["pali_name"],
            "slug": d["slug"],
            "parent_list_slug": d["parent_list_slug"],  # temporary
            "parent_list_id": None,  # will be filled
            "position_in_list": d["position_in_list"],
            "essay": d.get("essay", ""),
            "downstream_slugs": d.get("downstream", []),
            "downstream": [],
            "upstream_from_slugs": d.get("upstream_from", []),
            "upstream_from": [],
            "cross_references_slugs": d.get("cross_references", []),
            "cross_references": [],
            "tags": d.get("tags", []),
            "notes": d.get("notes", ""),
        }
        dhammas_to_insert.append(doc)

    if dhammas_to_insert:
        db.dhammas.insert_many(dhammas_to_insert)
    log.info("Inserted %d dhammas", len(dhammas_to_insert))

    # --- Build slug -> ObjectId lookup tables ---
    list_slug_to_id = {}
    for doc in db.lists.find({}, {"slug": 1}):
        list_slug_to_id[doc["slug"]] = doc["_id"]

    dhamma_slug_to_id = {}
    for doc in db.dhammas.find({}, {"slug": 1}):
        dhamma_slug_to_id[doc["slug"]] = doc["_id"]

    slug_to_id = {**list_slug_to_id, **dhamma_slug_to_id}

    # --- Resolve list references ---
    for doc in db.lists.find():
        children_ids = [
            dhamma_slug_to_id[s]
            for s in doc.get("children_slugs", [])
            if s in dhamma_slug_to_id
        ]
        upstream = []
        for ref in doc.get("upstream_from_slugs", []):
            ref_id = slug_to_id.get(ref.get("ref_slug"))
            if ref_id:
                upstream.append(
                    {
                        "ref_id": ref_id,
                        "ref_type": ref["ref_type"],
                        "relationship_note": ref.get("relationship_note", ""),
                    }
                )

        db.lists.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {"children": children_ids, "upstream_from": upstream},
                "$unset": {"children_slugs": "", "upstream_from_slugs": ""},
            },
        )

    # --- Resolve dhamma references ---
    for doc in db.dhammas.find():
        parent_id = list_slug_to_id.get(doc.get("parent_list_slug"))

        downstream = []
        for ref in doc.get("downstream_slugs", []):
            ref_id = slug_to_id.get(ref.get("ref_slug"))
            if ref_id:
                downstream.append(
                    {
                        "ref_id": ref_id,
                        "ref_type": ref["ref_type"],
                        "relationship_note": ref.get("relationship_note", ""),
                    }
                )

        upstream = []
        for ref in doc.get("upstream_from_slugs", []):
            ref_id = slug_to_id.get(ref.get("ref_slug"))
            if ref_id:
                upstream.append(
                    {
                        "ref_id": ref_id,
                        "ref_type": ref["ref_type"],
                        "relationship_note": ref.get("relationship_note", ""),
                    }
                )

        cross_refs = []
        for ref in doc.get("cross_references_slugs", []):
            ref_id = dhamma_slug_to_id.get(ref.get("ref_slug"))
            if ref_id:
                cross_refs.append(
                    {
                        "ref_id": ref_id,
                        "ref_type": ref["ref_type"],
                        "note": ref.get("note", ""),
                    }
                )

        db.dhammas.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "parent_list_id": parent_id,
                    "downstream": downstream,
                    "upstream_from": upstream,
                    "cross_references": cross_refs,
                },
                "$unset": {
                    "parent_list_slug": "",
                    "downstream_slugs": "",
                    "upstream_from_slugs": "",
                    "cross_references_slugs": "",
                },
            },
        )

    # --- Create indexes for common query patterns ---
    db.dhammas.create_index("slug", unique=True)
    db.dhammas.create_index("parent_list_id")
    db.lists.create_index("slug", unique=True)

    log.info("Resolved all slug references to ObjectIds")
    log.info("Created indexes on slug and parent_list_id")

    # --- Print summary ---
    list_count = db.lists.count_documents({})
    dhamma_count = db.dhammas.count_documents({})
    with_essays = db.dhammas.count_documents({"essay": {"$ne": ""}})
    with_downstream = db.dhammas.count_documents({"downstream.0": {"$exists": True}})
    with_crossrefs = db.dhammas.count_documents(
        {"cross_references.0": {"$exists": True}}
    )
    orphan_lists = db.lists.count_documents({"upstream_from.0": {"$exists": False}})

    print("\n" + "=" * 60)
    print("  SEED COMPLETE — Buddhist Dhammas Knowledge Graph")
    print("=" * 60)
    print(f"  Lists:             {list_count}")
    print(f"  Dhammas:           {dhamma_count}")
    print(f"  With essays:       {with_essays}")
    print(f"  With downstream:   {with_downstream}")
    print(f"  With cross-refs:   {with_crossrefs}")
    print(f"  Root lists:        {orphan_lists} (no upstream)")
    print("=" * 60)

    client.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point: parse spreadsheet, merge data, seed MongoDB."""
    if not SPREADSHEET.exists():
        log.error("Spreadsheet not found: %s", SPREADSHEET)
        sys.exit(1)

    log.info("Reading spreadsheet: %s", SPREADSHEET.name)

    # Parse both sheets
    df_nested = pd.read_excel(SPREADSHEET, sheet_name="Nested Lists", header=None)
    df_foundations = pd.read_excel(
        SPREADSHEET, sheet_name="Foundations & Cross-Cutting", header=None
    )

    lists_1, dhammas_1 = parse_nested_lists_sheet(df_nested)
    lists_2, dhammas_2 = parse_foundations_sheet(df_foundations)

    # Merge lists (deduplicate by slug)
    all_lists_map: dict[str, dict] = {}
    for lst in lists_1 + lists_2:
        slug = lst["slug"]
        if slug in all_lists_map:
            # Merge children from both sources
            existing = all_lists_map[slug]
            for child in lst["children"]:
                if child not in existing["children"]:
                    existing["children"].append(child)
            # Keep richer metadata
            if not existing["pali_name"] and lst["pali_name"]:
                existing["pali_name"] = lst["pali_name"]
        else:
            all_lists_map[slug] = lst

    # Merge dhammas (deduplicate by slug, keep first occurrence)
    all_dhammas_map: dict[str, dict] = {}
    for d in dhammas_1 + dhammas_2:
        slug = d["slug"]
        if slug not in all_dhammas_map:
            all_dhammas_map[slug] = d
        else:
            # Merge any missing fields
            existing = all_dhammas_map[slug]
            if not existing["pali_name"] and d["pali_name"]:
                existing["pali_name"] = d["pali_name"]
            if not existing["notes"] and d["notes"]:
                existing["notes"] = d["notes"]

    all_lists = list(all_lists_map.values())
    all_dhammas = list(all_dhammas_map.values())

    log.info("Merged: %d lists, %d dhammas", len(all_lists), len(all_dhammas))

    # Detect cross-references via shared Pali terms
    detect_cross_references(all_dhammas)

    # Assign positions within each list
    assign_positions(all_lists, all_dhammas)

    # Seed MongoDB
    seed_database(all_lists, all_dhammas)


if __name__ == "__main__":
    main()
