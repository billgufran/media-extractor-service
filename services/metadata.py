import os
import re
from typing import Any

import requests
from rapidfuzz import fuzz

TMDB_API_KEY = os.getenv("TMDB_API_KEY") or ""
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
TMDB_API_URL = "https://api.themoviedb.org/3"


def _clean_title(text: str) -> str:
    """Remove parenthetical info like ' (film)' from a title."""
    return re.sub(r"\s*\([^\)]*\)$", "", text).strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _parse_year(value: object | None) -> int | None:
    if not value:
        return None
    try:
        # TMDB returns YYYY-MM-DD for movies and TV first_air_date
        return int(str(value)[:4])
    except Exception:
        return None
    

def _refine_query(title: str) -> str:
    """Lightly normalize user input for downstream APIs."""
    # Strip trailing parentheticals and common noise words
    t = _clean_title(title)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _has_generic_first_hint(query: str) -> bool:
    """Detect queries like 'series 1', '1', 'first' without explicit 'part'."""
    q = _normalize(query)

    tokens = set(re.findall(r"\w+", q))
    explicit_part_words = {"part", "episode", "season", "volume", "book", "chapter"}

    if tokens & explicit_part_words:
        return False
    
    first_words = {"1", "1st", "first", "one"}
    roman_first = {"i"}
    
    return bool((tokens & first_words) or (tokens & roman_first))


def _select_best_tmdb_match(
    query: str, items: list[dict[str, Any]], *, is_tv: bool = False
) -> dict[str, Any] | None:
    """
    Choose the best TMDB search result using fuzzy matching and simple heuristics.

    Heuristics:
    - If the query implies the first installment (e.g., contains '1' or 'first' without 'part'),
      prefer the earliest release among candidates containing the base tokens.
    - Otherwise, use WRatio against cleaned title/name, break ties by popularity and vote_count.
    """
    if not items:
        return None

    # Candidate title field names differ between movie and TV results
    title_keys = ["name", "original_name"] if is_tv else ["title", "original_title"]

    # Build candidates with computed fields
    candidates: list[dict[str, Any]] = []
    for it in items:
        raw_title_val = next((it.get(k) for k in title_keys if it.get(k)), "")
        raw_title = str(raw_title_val)
        cleaned = _clean_title(raw_title)
        year = _parse_year(it.get("first_air_date" if is_tv else "release_date"))
        candidates.append(
            {
                "item": it,
                "raw_title": raw_title or "",
                "title": cleaned,
                "year": year,
                "popularity": it.get("popularity", 0) or 0,
                "vote_count": it.get("vote_count", 0) or 0,
            }
        )

    # If query hints "first installment" (e.g. '1', 'first'), pick earliest release
    if _has_generic_first_hint(query):
        # Base tokens = query minus numbers and installment markers
        q = _normalize(query)
        base_tokens = [
            t
            for t in re.findall(r"\w+", q)
            if t not in {"1", "1st", "first", "one", "part", "episode", "season", "volume", "book", "chapter", "film", "movie", "tv"}
            and not t.isdigit()
        ]
        def contains_all_tokens(title: str) -> bool:
            t = _normalize(title)
            return all(bt in t for bt in base_tokens) if base_tokens else True

        scoped = [c for c in candidates if contains_all_tokens(c["title"])] or candidates
        scoped.sort(key=lambda c: (c["year"] if c["year"] is not None else 10**9, -c["popularity"]))
        return scoped[0]["item"]

    # Otherwise choose by fuzzy score then popularity
    norm_q = _normalize(_clean_title(query))
    for c in candidates:
        c["score"] = fuzz.WRatio(norm_q, _normalize(c["title"]))

    candidates.sort(key=lambda c: (c["score"], c["vote_count"], c["popularity"]), reverse=True)
    
    return candidates[0]["item"]


def _get_book_fields(item: dict[str, Any]) -> dict[str, Any]:
    book_object = item.get("volumeInfo")
    book = book_object if isinstance(book_object, dict) else {}

    raw_title = book.get("title")
    title = _clean_title(str(raw_title)) if raw_title is not None else ""

    year = _parse_year(book.get("publishedDate"))

    raw_rating_count = book.get("ratingsCount")
    if isinstance(raw_rating_count, (int, float)):
        ratings_count = int(raw_rating_count)
    elif isinstance(raw_rating_count, str):
        try:
            ratings_count = int(float(raw_rating_count))
        except ValueError:
            ratings_count = 0
    else:
        ratings_count = 0
        
    raw_average_rating = book.get("averageRating")
    try:
        avg_rating = float(raw_average_rating) if raw_average_rating is not None else 0.0
    except (TypeError, ValueError):
        avg_rating = 0.0

    return {
        "title": title,
        "year": year,
        "ratings_count": ratings_count,
        "avg_rating": avg_rating,
    }


def _select_best_book_match(query: str, items: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose the best Google Books result using fuzzy matching and heuristics.

    Heuristics mirror TMDB selection:
    - If query hints the first installment (generic '1'/'first' without explicit part words),
      prefer earliest published date among candidates matching base tokens.
    - Otherwise, use WRatio against cleaned title; break ties by ratingsCount and averageRating.
    """
    if not items:
        return None

    candidates: list[dict[str, Any]] = []
    for it in items:
        fields = _get_book_fields(it)
        candidates.append({"item": it, **fields})

    if _has_generic_first_hint(query):
        q = _normalize(query)
        base_tokens = [
            t
            for t in re.findall(r"\w+", q)
            if t
            not in {
                "1",
                "1st",
                "first",
                "one",
                "part",
                "episode",
                "season",
                "volume",
                "book",
                "chapter",
                "film",
                "movie",
                "tv",
            }
            and not t.isdigit()
        ]

        def contains_all_tokens(title: str) -> bool:
            t = _normalize(title)
            return all(bt in t for bt in base_tokens) if base_tokens else True

        scoped = [c for c in candidates if contains_all_tokens(c["title"])] or candidates
        scoped.sort(
            key=lambda c: (
                c["year"] if c["year"] is not None else 10**9,
                -c["ratings_count"],
                -c["avg_rating"],
            )
        )
        return scoped[0]["item"]

    norm_q = _normalize(_clean_title(query))
    for c in candidates:
        c["score"] = fuzz.WRatio(norm_q, _normalize(c["title"]))

    candidates.sort(
        key=lambda c: (c["score"], c["ratings_count"], c["avg_rating"]),
        reverse=True,
    )

    return candidates[0]["item"]

def fetch_movie_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        params: dict[str, Any] = {
            "api_key": TMDB_API_KEY,
            "include_adult": "false",
            "language": "en-US",
            "query": refined,
        }
        if year is not None:
            params["year"] = year

        res_json: Any = requests.get(
            f"{TMDB_API_URL}/search/movie", params=params, timeout=30
        ).json()
        results_field = res_json.get("results") if isinstance(res_json, dict) else None
        items: list[dict[str, Any]] = [i for i in (results_field or []) if isinstance(i, dict)]

        if items:
            selected = _select_best_tmdb_match(refined, items, is_tv=False) or items[0]
            return {
                "title": _clean_title(
                    str(
                        selected.get("title")
                        or selected.get("original_title")
                        or refined
                    )
                ),
                "description": str(selected.get("overview", "")),
                "year": str(selected.get("release_date", "")),
            }
        # No results: return a typed, consistent fallback
        return {"title": refined, "description": "", "year": ""}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_tv_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        params: dict[str, Any] = {
            "api_key": TMDB_API_KEY,
            "include_adult": "false",
            "language": "en-US",
            "query": refined,
        }
        if year is not None:
            params["year"] = year

        res_json: Any = requests.get(
            f"{TMDB_API_URL}/search/tv", params=params, timeout=30
        ).json()
        results_field = res_json.get("results") if isinstance(res_json, dict) else None
        items: list[dict[str, Any]] = [i for i in (results_field or []) if isinstance(i, dict)]

        if items:
            selected = _select_best_tmdb_match(refined, items, is_tv=True) or items[0]
            return {
                "title": _clean_title(
                    str(
                        selected.get("name")
                        or selected.get("original_name")
                        or refined
                    )
                ),
                "description": str(selected.get("overview", "")),
                "year": str(selected.get("first_air_date", "")),
            }
        # No results: return a typed, consistent fallback
        return {"title": refined, "description": "", "year": ""}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def get_book_title(item: object) -> str:
    if isinstance(item, dict):
        vi = item.get("volumeInfo")
        if isinstance(vi, dict):
            title_val = vi.get("title")
            if title_val is not None:
                return str(title_val)

    if isinstance(item, str):
        return item

    return ""

def fetch_book_metadata(title: str, author: str | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        q = refined if not author else f"{refined} inauthor:{author}"
        res_json: Any = requests.get(
            GOOGLE_BOOKS_API_URL, params={"q": q}, timeout=30
        ).json()
        items_field = res_json.get("items") if isinstance(res_json, dict) else None
        items: list[dict[str, Any]] = [i for i in (items_field or []) if isinstance(i, dict)]

        if items:
            # Apply the same fuzzy/heuristic logic as movies/TV
            selected = _select_best_book_match(refined, items) or items[0]
            vi_obj = selected.get("volumeInfo")
            vi = vi_obj if isinstance(vi_obj, dict) else {}
            authors_val = vi.get("authors")
            authors_list: list[str] = [str(a) for a in authors_val] if isinstance(authors_val, list) else []
            joined_authors = ", ".join(authors_list)
            return {
                "title": _clean_title(str(vi.get("title") or refined)),
                "author": joined_authors,
                "description": str(vi.get("description", "")),
                "year": str(vi.get("publishedDate", "")),
            }
        # No results: return a typed, consistent fallback
        return {"title": refined, "author": "", "description": "", "year": ""}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_metadata(
    media_type: str, title: str, year: int | None = None, author: str | None = None
) -> dict[str, str]:
    metadata: dict[str, str] = {}

    if media_type == "movie":
        metadata = fetch_movie_metadata(title, year)
    elif media_type == "tv":
        metadata = fetch_tv_metadata(title, year)
    elif media_type == "book":
        metadata = fetch_book_metadata(title, author)

    metadata_title = metadata.get("title", title)

    return {
        **metadata,
        "title": metadata_title,
        "type": media_type,
        "description": metadata.get("description", ""),
    }
