# RCA: Inconsistent Pali Word Formatting in Essays

## Problem Statement
Pali words within essay text display inconsistently: some have literal asterisks (`*vedanā*`), some have double quotes (`"thina-middha"`), and some have no formatting. Users see raw markdown artifacts instead of properly italicized text.

## Root Cause
Two compounding issues:
1. **Source data inconsistency**: AI-generated essays used two different conventions for Pali words — markdown italic `*word*` and quoted `"word"` — across 118 essay files
2. **Missing markdown rendering**: Frontend renders essays as plain text via `{data.current.essay}` with `white-space: pre-wrap` CSS, so `*word*` displays as literal asterisks

## Impact
- **Severity**: Medium — visual inconsistency, not data loss
- **Scope**: ~70 essays with `*pali*` patterns, ~49 essays with `"pali"` patterns
- **Frequency**: Every page view of an affected essay

## Fix Strategy
1. Normalize all essay files: convert `"pali"` → `*pali*` for known Pali words
2. Add lightweight inline italic renderer to NavigationLayout.tsx essay display
3. The `*word*` → `<em>word</em>` transform handles all Pali words uniformly

## Prevention
- Essay generation prompt should specify formatting convention
- Frontend should support basic inline markdown in essay content
