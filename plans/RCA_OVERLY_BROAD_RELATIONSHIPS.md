# RCA: Overly Broad List-to-List Relationships

## Problem Statement
Some dhammas link downstream to entire lists when they should only link to specific subset members. Example: `ethics` (from Three Trainings) links to the entire Noble Eightfold Path (8 items) instead of just Right Speech, Right Action, Right Livelihood (3 items).

## Root Cause
`_detect_column_downstream()` in seed_db.py (line 438-511) wires a dhamma to the whole list whenever column co-occurrence is detected, without filtering to only the specific children that actually appear on that dhamma's rows.

Additionally, a comment at lines 498-501 documents that col 0→col 1 (Noble Truths → Three Trainings) should be skipped, but no code implements the skip.

## Affected Relationships (6 instances)
| Dhamma | Links To (wrong) | Should Link To (correct) |
|--------|------------------|--------------------------|
| ethics | noble-eightfold-path (all 8) | right-speech, right-action, right-livelihood |
| concentration | noble-eightfold-path (all 8) | right-effort, right-mindfulness, right-concentration |
| wisdom | noble-eightfold-path (all 8) | right-view, right-intention |
| right-action | five-precepts (all 5) | non-harming, non-stealing, sexual-responsibility |
| right-speech | five-precepts (all 5) | non-lying |
| right-livelihood | five-precepts (all 5) | abstinence-from-intoxicants |

## Fix Strategy
Add partial-list downstream support in `apply_corrections()`: for these known relationships, wire each dhamma to specific children (as dhammas, not lists), replacing the overly broad list-level connections.

## Prevention
- Column co-occurrence detection should pass through which specific children co-occur
- Semantic validation step should check that downstream relationships are doctrinally accurate
