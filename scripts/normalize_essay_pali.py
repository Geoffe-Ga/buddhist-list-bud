#!/usr/bin/env python3
"""One-time script to normalize Pali word formatting in essay files.

Converts "pali_word" → *pali_word* for known Pali terms, so the
frontend can render them as italics via <em> tags.

Safe to run multiple times (idempotent).
"""

import re
from pathlib import Path

ESSAYS_DIR = Path(__file__).parent.parent / "data" / "essays"

# Known Pali terms that appear in double quotes in essays.
# Each will be converted from "term" to *term*.
KNOWN_PALI_TERMS = {
    "cakkhu",
    "Bojjhanga",
    "moha",
    "avijja",
    "mano",
    "mano-dhamma",
    "saddha",
    "kāmacchanda",
    "Samma Vayama",
    "samma",
    "vayama",
    "pañña",
    "tanha",
    "nekkhamma",
    "vyāpāda",
    "kamesu micchacara veramani",
    "kamesu",
    "micchacara",
    "veramani",
    "kāya",
    "Cattaro Satipatthana",
    "viññāṇa",
    "samma samadhi",
    "samadhi",
    "upekkha",
    "Samma Ditthi",
    "chanda",
    "sankhara-dukkha",
    "sankhara",
    "dukkha",
    "Dukkha",
    "viriya",
    "Adinnadana veramani",
    "Samma Vaca",
    "vaca",
    "thina-middha",
    "thina",
    "middha",
    "Dhamma",
    "dhamma",
    "pīti",
    "Panatipata veramani",
    "anatta",
    "Samma Sati",
    "sati",
    "kāyagatāsati",
    "Samma Ajiva",
    "ajiva",
    "vedanā",
    "anagami",
    "vicikicchā",
    "Cattaro Sammappadhana",
    "Samma Kammanta",
    "kammanta",
    "Ariya Atthangika Magga",
    "kama",
    "raga",
    "Sangha",
    "sota",
    "jara-marana",
    "jara",
    "marana",
    "citta",
    "Surameraya veramani",
    "metta",
    "ghāna",
    "gandha",
    "jivhā",
    "rasa",
    "Nirodha",
    "Viriya",
}


def normalize_essay(text: str) -> str:
    """Replace "pali_term" with *pali_term* for all known Pali terms.

    Handles trailing punctuation inside quotes, e.g. "thina-middha." → *thina-middha*.
    """
    for term in sorted(KNOWN_PALI_TERMS, key=len, reverse=True):
        # Replace "term" with *term* (exact match)
        quoted = f'"{term}"'
        italic = f"*{term}*"
        text = text.replace(quoted, italic)

        # Replace "term." or "term," (trailing punct inside quotes)
        # Move the punctuation outside: "term." → *term*.
        pattern = re.compile(rf'"{re.escape(term)}([.,;:!?])"')
        text = pattern.sub(rf"*{term}*\1", text)
    return text


def main() -> None:
    """Normalize all essay files."""
    changed = 0
    for essay_path in sorted(ESSAYS_DIR.glob("*.md")):
        original = essay_path.read_text(encoding="utf-8")
        normalized = normalize_essay(original)
        if normalized != original:
            essay_path.write_text(normalized, encoding="utf-8")
            changed += 1
            print(f"  Fixed: {essay_path.name}")

    print(f"\nNormalized {changed} essay files")


if __name__ == "__main__":
    main()
