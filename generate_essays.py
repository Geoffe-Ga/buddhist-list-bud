#!/usr/bin/env python3
"""
generate_essays.py — Generate beginner-friendly essays for each dhamma.

Reads the spreadsheet to identify all dhammas, then calls the Anthropic API
to generate a 150-300 word essay for each one. Essays are saved as individual
markdown files in data/essays/{slug}.md.

IDEMPOTENT: Skips dhammas that already have essay files (use --force to regenerate).
COST: ~$0.50-1.00 for a full run (~150-200 dhammas).
TIME: ~10-15 minutes (rate-limited API calls).

Each essay includes:
    - Plain English explanation of the concept
    - A practical example or analogy
    - The Pali term and its meaning
    - Why this teaching matters on the Buddhist path
    - Warm, accessible tone suitable for beginners

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python generate_essays.py              # Generate missing essays only
    python generate_essays.py --force      # Regenerate all essays
    python generate_essays.py --dry-run    # Show what would be generated
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# We import anthropic inside generate() so the script can be imported
# for testing without requiring the API key.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

SPREADSHEET = Path(__file__).parent / "buddhist_list_bud_content_v1.xlsx"
ESSAYS_DIR = Path(__file__).parent / "data" / "essays"

# Essay generation prompt template.
# This produces consistent, high-quality essays that are beginner-friendly
# while being doctrinally accurate to the Theravada tradition.
ESSAY_PROMPT = """You are a warm, knowledgeable teacher of \
Theravada Buddhism writing for Western beginners who have \
no prior knowledge of Buddhist terminology.

Write a 150-300 word essay about the Buddhist concept: "{name}" (Pali: {pali_name}).

Context:
- This concept belongs to the list: {parent_list}
- Additional notes: {notes}

Requirements:
1. Start with what this concept means in plain English
2. Include the Pali term and explain what it literally means
3. Give a practical, relatable example or analogy from everyday life
4. Explain why this teaching matters on the path to awakening
5. Keep the tone warm, encouraging, and accessible — like a friend explaining over tea
6. Do NOT use bullet points or numbered lists — write in flowing paragraphs
7. Do NOT include a title or heading — just the essay text
8. Stay within 150-300 words

Write the essay now:"""


def collect_dhammas_from_spreadsheet() -> list[dict]:
    """Extract all unique dhammas from both sheets of the spreadsheet.

    Returns a list of dicts with keys: name, pali_name, slug, parent_list, notes.
    This mirrors the parsing logic in seed_db.py but is simpler — we just need
    enough info to generate good essay prompts.
    """
    # Import slugify from seed_db to stay consistent
    from seed_db import (
        extract_pali_from_name,
        parse_header,
        slugify,
        strip_number_prefix,
    )

    dhammas = {}  # slug -> dhamma info

    # --- Sheet 1: Nested Lists ---
    df = pd.read_excel(SPREADSHEET, sheet_name="Nested Lists", header=None)
    header_row = df.iloc[0]

    # Parse column headers to know parent list names
    col_to_list = {}
    for col_idx in range(9):
        val = header_row.iloc[col_idx]
        if not pd.isna(val):
            name, _ = parse_header(str(val))
            col_to_list[col_idx] = name

    for row_idx in range(1, len(df)):
        row = df.iloc[row_idx]

        # Find deepest main-column value for parent list context
        parent_list = ""
        deepest_name = ""
        for col_idx in range(8, -1, -1):
            val = row.iloc[col_idx]
            if col_idx in col_to_list and not pd.isna(val):
                parent_list = col_to_list[col_idx]
                name_raw, pali = extract_pali_from_name(str(val).strip())
                clean = strip_number_prefix(name_raw)
                slug = slugify(clean)
                if slug and slug not in dhammas:
                    dhammas[slug] = {
                        "name": clean,
                        "pali_name": pali,
                        "slug": slug,
                        "parent_list": parent_list,
                        "notes": "",
                    }
                if not deepest_name:
                    deepest_name = clean
                break

        # Expansion items (column 9)
        expansion = row.iloc[9] if not pd.isna(row.iloc[9]) else None
        pali_term = str(row.iloc[10]).strip() if not pd.isna(row.iloc[10]) else ""
        notes = str(row.iloc[11]).strip() if not pd.isna(row.iloc[11]) else ""

        if expansion:
            exp_name_raw, exp_pali = extract_pali_from_name(str(expansion).strip())
            exp_name = strip_number_prefix(exp_name_raw)
            exp_slug = slugify(exp_name)
            if not exp_pali:
                exp_pali = pali_term

            if exp_slug and exp_slug not in dhammas:
                dhammas[exp_slug] = {
                    "name": exp_name,
                    "pali_name": exp_pali,
                    "slug": exp_slug,
                    "parent_list": parent_list or "Nested Lists",
                    "notes": notes,
                }

    # --- Sheet 2: Foundations & Cross-Cutting ---
    df2 = pd.read_excel(
        SPREADSHEET, sheet_name="Foundations & Cross-Cutting", header=None
    )
    for row_idx in range(1, len(df2)):
        row = df2.iloc[row_idx]
        list_name = row.iloc[0] if not pd.isna(row.iloc[0]) else None
        item_name = row.iloc[1] if not pd.isna(row.iloc[1]) else None
        pali = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else ""
        notes = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else ""

        if not list_name or not item_name:
            continue

        item_clean, item_pali = extract_pali_from_name(str(item_name).strip())
        if not item_pali:
            item_pali = pali
        slug = slugify(item_clean)
        list_clean, _ = extract_pali_from_name(str(list_name).strip())

        if slug and slug not in dhammas:
            dhammas[slug] = {
                "name": item_clean,
                "pali_name": item_pali,
                "slug": slug,
                "parent_list": list_clean,
                "notes": notes,
            }

    return list(dhammas.values())


def generate_essay(client, dhamma: dict) -> str:
    """Call Claude Sonnet to generate a single essay.

    Args:
        client: An anthropic.Anthropic client instance.
        dhamma: Dict with name, pali_name, parent_list, notes, slug.

    Returns:
        The generated essay text.
    """
    prompt = ESSAY_PROMPT.format(
        name=dhamma["name"],
        pali_name=dhamma["pali_name"] or "(no Pali term recorded)",
        parent_list=dhamma["parent_list"],
        notes=dhamma["notes"] or "No additional notes",
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


def main() -> None:
    """Generate essays for all dhammas found in the spreadsheet."""
    parser = argparse.ArgumentParser(
        description="Generate beginner-friendly essays for Buddhist dhammas"
    )
    parser.add_argument(
        "--force", action="store_true", help="Regenerate all essays (even existing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without calling the API",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        log.error(
            "ANTHROPIC_API_KEY not set. Export it or create a .env file.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)

    if not SPREADSHEET.exists():
        log.error("Spreadsheet not found: %s", SPREADSHEET)
        sys.exit(1)

    ESSAYS_DIR.mkdir(parents=True, exist_ok=True)

    dhammas = collect_dhammas_from_spreadsheet()
    log.info("Found %d unique dhammas in spreadsheet", len(dhammas))

    # Determine which essays to generate
    to_generate = []
    for d in dhammas:
        essay_path = ESSAYS_DIR / f"{d['slug']}.md"
        if essay_path.exists() and not args.force:
            continue
        to_generate.append(d)

    existing = len(dhammas) - len(to_generate)
    log.info(
        "Essays to generate: %d (skipping %d existing)", len(to_generate), existing
    )

    if args.dry_run:
        print("\n--- DRY RUN: Would generate essays for ---")
        for d in to_generate:
            print(f"  {d['slug']:40s}  {d['name']} ({d['pali_name']})")
        print(f"\nTotal: {len(to_generate)} essays")
        return

    if not to_generate:
        print("All essays already exist. Use --force to regenerate.")
        return

    # Initialize the Anthropic client
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    generated = 0
    errors = 0

    for i, d in enumerate(to_generate, 1):
        slug = d["slug"]
        essay_path = ESSAYS_DIR / f"{slug}.md"

        try:
            log.info(
                "[%d/%d] Generating: %s (%s)",
                i,
                len(to_generate),
                d["name"],
                d["pali_name"],
            )
            essay = generate_essay(client, d)
            essay_path.write_text(essay, encoding="utf-8")
            generated += 1
            log.info("  Saved: %s (%d words)", essay_path.name, len(essay.split()))

            # Brief pause to respect rate limits
            time.sleep(0.5)

        except Exception as e:
            log.error("  Failed for %s: %s", slug, e)
            errors += 1
            time.sleep(2)  # longer pause after errors

    print(f"\nDone! Generated {generated} essays, {errors} errors.")
    if errors:
        print("Re-run to retry failed essays (idempotent).")


if __name__ == "__main__":
    main()
