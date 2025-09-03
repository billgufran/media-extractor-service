from __future__ import annotations

from typing import Any

from services.metadata import (
    _has_generic_first_hint,
    _refine_query,
    _select_best_tmdb_match,
)


def test_refine_query_strips_parenthetical_and_whitespace() -> None:
    assert _refine_query("The Matrix (film)") == "The Matrix"  # nosec B101


def test_has_generic_first_hint_detects_first_installment() -> None:
    assert _has_generic_first_hint("Series 1")  # nosec B101
    assert _has_generic_first_hint("First")  # nosec B101
    assert not _has_generic_first_hint("Series Part 1")  # nosec B101
    assert not _has_generic_first_hint("Episode 1")  # nosec B101


def test_select_best_tmdb_match_prefers_earliest_for_first_hint() -> None:
    items: list[dict[str, Any]] = [
        {"title": "Example", "release_date": "2000-01-01", "popularity": 10, "vote_count": 1},
        {"title": "Example", "release_date": "1990-01-01", "popularity": 5, "vote_count": 1},
    ]
    selected = _select_best_tmdb_match("Example 1", items, is_tv=False)
    assert selected is not None  # nosec B101
    assert selected == items[1]  # nosec B101


def test_select_best_tmdb_match_uses_fuzzy_score_then_popularity() -> None:
    items: list[dict[str, Any]] = [
        {"title": "Example Movie", "release_date": "2000-01-01", "popularity": 1, "vote_count": 1},
        {"title": "Different Title", "release_date": "2001-01-01", "popularity": 100, "vote_count": 1},
    ]
    selected = _select_best_tmdb_match("Example Movie", items, is_tv=False)
    assert selected is not None  # nosec B101
    assert selected == items[0]  # nosec B101
