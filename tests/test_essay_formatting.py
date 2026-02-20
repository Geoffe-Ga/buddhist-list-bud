"""Tests for essay Pali word formatting normalization.

Verifies that all Pali words in essay files use consistent *italic*
formatting (no double quotes around Pali terms, no bare Pali without
formatting markers).
"""

import re
from pathlib import Path

ESSAYS_DIR = Path(__file__).parent.parent / "data" / "essays"

# Known Pali words/phrases that appear in essays.
# These should always be wrapped in *asterisks* for italic rendering,
# never in "double quotes".
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
}


def _find_quoted_pali_in_essay(text: str) -> list[str]:
    """Find Pali terms wrapped in double quotes within essay text."""
    # Match "word" patterns
    quoted = re.findall(r'"([^"]+)"', text)
    return [q for q in quoted if q in KNOWN_PALI_TERMS]


def test_no_quoted_pali_in_essays() -> None:
    """No essay file should contain Pali words in double quotes."""
    violations: list[str] = []
    for essay_path in sorted(ESSAYS_DIR.glob("*.md")):
        text = essay_path.read_text(encoding="utf-8")
        quoted_pali = _find_quoted_pali_in_essay(text)
        for term in quoted_pali:
            violations.append(f'{essay_path.name}: "{term}" should be *{term}*')

    assert not violations, (
        f"Found {len(violations)} Pali words in double quotes "
        f"(should be *italic*):\n" + "\n".join(violations)
    )


def test_asterisk_pali_words_present() -> None:
    """Pali words that were previously quoted should now use *italic* markers."""
    # Spot-check a few key essays that we know had quoted Pali
    checks = {
        "feeling.md": "vedanā",
        "sloth-and-torpor.md": "thina-middha",
        "delusion-ignorance.md": "moha",
        "craving.md": "tanha",
    }
    for filename, pali_term in checks.items():
        essay_path = ESSAYS_DIR / filename
        if not essay_path.exists():
            continue
        text = essay_path.read_text(encoding="utf-8")
        assert (
            f"*{pali_term}*" in text
        ), f"{filename} should contain *{pali_term}* (italic Pali)"
