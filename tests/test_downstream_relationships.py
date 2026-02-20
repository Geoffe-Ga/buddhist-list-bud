"""Tests for partial-list downstream relationship correctness.

Verifies that dhammas like ethics/concentration/wisdom link to only
their correct subset of the Noble Eightfold Path, not the entire list.
Same for right-action/right-speech/right-livelihood → Five Precepts.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

# Import seed_db functions under test
SEED_DB_PATH = Path(__file__).parent.parent / "seed_db.py"
SPREADSHEET = Path(__file__).parent.parent / "buddhist_list_bud_content_v1.xlsx"


@pytest.fixture()
def parsed_data():
    """Parse spreadsheet and apply corrections, returning (lists_map, dhammas_map)."""
    # We need to import seed_db dynamically since it's not a package
    import importlib.util

    spec = importlib.util.spec_from_file_location("seed_db", SEED_DB_PATH)
    seed_db = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed_db)

    df_nested = pd.read_excel(SPREADSHEET, sheet_name="Nested Lists", header=None)
    df_foundations = pd.read_excel(
        SPREADSHEET, sheet_name="Foundations & Cross-Cutting", header=None
    )

    lists_1, dhammas_1 = seed_db.parse_nested_lists_sheet(df_nested)
    lists_2, dhammas_2 = seed_db.parse_foundations_sheet(df_foundations)

    # Merge
    all_lists_map = {}
    for lst in lists_1 + lists_2:
        slug = lst["slug"]
        if slug in all_lists_map:
            existing = all_lists_map[slug]
            for child in lst["children"]:
                if child not in existing["children"]:
                    existing["children"].append(child)
            if not existing["pali_name"] and lst["pali_name"]:
                existing["pali_name"] = lst["pali_name"]
        else:
            all_lists_map[slug] = lst

    all_dhammas_map = {}
    for d in dhammas_1 + dhammas_2:
        slug = d["slug"]
        if slug not in all_dhammas_map:
            all_dhammas_map[slug] = d
        else:
            existing = all_dhammas_map[slug]
            if not existing["pali_name"] and d["pali_name"]:
                existing["pali_name"] = d["pali_name"]

    seed_db.apply_corrections(all_lists_map, all_dhammas_map)
    return all_lists_map, all_dhammas_map


def _downstream_ref_slugs(dhamma: dict) -> list[str]:
    """Extract all downstream ref slugs from a dhamma."""
    return [ref["ref_slug"] for ref in dhamma.get("downstream", [])]


def _downstream_ref_types(dhamma: dict) -> dict[str, str]:
    """Map ref_slug -> ref_type for all downstream refs."""
    return {ref["ref_slug"]: ref["ref_type"] for ref in dhamma.get("downstream", [])}


class TestThreeTrainingsToEightfoldPath:
    """Three Trainings members should link to specific Eightfold Path subsets."""

    def test_ethics_links_to_sila_triad(self, parsed_data):
        """Ethics should link to right-speech, right-action, right-livelihood only."""
        _, dhammas = parsed_data
        ethics = dhammas["ethics"]
        downstream = _downstream_ref_slugs(ethics)
        sila_triad = {"right-speech", "right-action", "right-livelihood"}

        # Should contain all three sila members
        for member in sila_triad:
            assert member in downstream, (
                f"ethics should link downstream to {member}"
            )

        # Should NOT link to the entire noble-eightfold-path list
        assert "noble-eightfold-path" not in downstream, (
            "ethics should NOT link to the entire noble-eightfold-path list"
        )

    def test_concentration_links_to_samadhi_triad(self, parsed_data):
        """Concentration should link to right-effort, right-mindfulness, right-concentration."""
        _, dhammas = parsed_data
        conc = dhammas["concentration"]
        downstream = _downstream_ref_slugs(conc)
        samadhi_triad = {"right-effort", "right-mindfulness", "right-concentration"}

        for member in samadhi_triad:
            assert member in downstream, (
                f"concentration should link downstream to {member}"
            )

        assert "noble-eightfold-path" not in downstream, (
            "concentration should NOT link to the entire noble-eightfold-path list"
        )

    def test_wisdom_links_to_panna_dyad(self, parsed_data):
        """Wisdom should link to right-view and right-intention only."""
        _, dhammas = parsed_data
        wisdom = dhammas["wisdom"]
        downstream = _downstream_ref_slugs(wisdom)
        panna_dyad = {"right-view", "right-intention"}

        for member in panna_dyad:
            assert member in downstream, (
                f"wisdom should link downstream to {member}"
            )

        assert "noble-eightfold-path" not in downstream, (
            "wisdom should NOT link to the entire noble-eightfold-path list"
        )


class TestEightfoldPathToFivePrecepts:
    """Eightfold Path members should link to specific Five Precepts subsets."""

    def test_right_action_links_to_body_precepts(self, parsed_data):
        """Right Action should link to non-harming, non-stealing, sexual-responsibility."""
        _, dhammas = parsed_data
        ra = dhammas["right-action"]
        downstream = _downstream_ref_slugs(ra)
        body_precepts = {"non-harming", "non-stealing", "sexual-responsibility"}

        for member in body_precepts:
            assert member in downstream, (
                f"right-action should link downstream to {member}"
            )

        assert "five-precepts" not in downstream, (
            "right-action should NOT link to the entire five-precepts list"
        )

    def test_right_speech_links_to_non_lying(self, parsed_data):
        """Right Speech should link to non-lying."""
        _, dhammas = parsed_data
        rs = dhammas["right-speech"]
        downstream = _downstream_ref_slugs(rs)

        assert "non-lying" in downstream, (
            "right-speech should link downstream to non-lying"
        )

        assert "five-precepts" not in downstream, (
            "right-speech should NOT link to the entire five-precepts list"
        )

    def test_right_livelihood_no_precept_link(self, parsed_data):
        """Right Livelihood should NOT link to Five Precepts at all.

        Right Livelihood prohibits *trade* in intoxicants (AN 5.177), while
        the 5th Precept prohibits *consuming* them. No standard commentarial
        source maps Right Livelihood to any specific precept.
        """
        _, dhammas = parsed_data
        rl = dhammas["right-livelihood"]
        downstream = _downstream_ref_slugs(rl)

        assert "five-precepts" not in downstream, (
            "right-livelihood should NOT link to five-precepts list"
        )
        assert "abstinence-from-intoxicants" not in downstream, (
            "right-livelihood should NOT link to abstinence-from-intoxicants "
            "(selling vs. consuming intoxicants are different ethical concerns)"
        )

    def test_downstream_refs_are_dhamma_type(self, parsed_data):
        """Partial-list downstream refs should have ref_type 'dhamma', not 'list'."""
        _, dhammas = parsed_data
        # Check ethics -> sila triad uses dhamma type
        ethics = dhammas["ethics"]
        ref_types = _downstream_ref_types(ethics)
        for slug in ["right-speech", "right-action", "right-livelihood"]:
            if slug in ref_types:
                assert ref_types[slug] == "dhamma", (
                    f"ethics -> {slug} should be ref_type 'dhamma'"
                )
