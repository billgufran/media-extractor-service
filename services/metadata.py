import os
import requests
import re
from rapidfuzz import fuzz, process

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
TMDB_API_URL = "https://api.themoviedb.org/3"


def _clean_title(text: str) -> str:
    """Remove parenthetical info like ' (film)' from a title."""
    return re.sub(r"\s*\([^\)]*\)$", "", text).strip()


def _normalize(text: str) -> str:
    """Lowercase and strip extra spaces for fuzzy matching."""
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        # TMDB returns YYYY-MM-DD for movies and TV first_air_date
        return int(str(value)[:4])
    except Exception:
        return None


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


def _select_best_tmdb_match(query: str, items: list[dict], *, is_tv: bool = False) -> dict | None:
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
    candidates: list[dict] = []
    for it in items:
        raw_title = next((it.get(k) for k in title_keys if it.get(k)), "")
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


def _refine_query(title: str) -> str:
    """Lightly normalize user input for downstream APIs."""
    # Strip trailing parentheticals and common noise words
    t = _clean_title(title)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def fetch_movie_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        req_url = f"{TMDB_API_URL}/search/movie?api_key={TMDB_API_KEY}&include_adult=false&language=en-US&query={requests.utils.quote(refined)}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url, timeout=30).json()
        items = res.get("results", [])

        if items:
            selected = _select_best_tmdb_match(refined, items, is_tv=False) or items[0]
            return {
                "title": _clean_title(selected.get("title") or selected.get("original_title") or refined),
                "description": selected.get("overview", ""),
                "year": selected.get("release_date", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_tv_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        req_url = f"{TMDB_API_URL}/search/tv?api_key={TMDB_API_KEY}&include_adult=false&language=en-US&query={requests.utils.quote(refined)}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url, timeout=30).json()
        items = res.get("results", [])

        if items:
            selected = _select_best_tmdb_match(refined, items, is_tv=True) or items[0]
            return {
                "title": _clean_title(selected.get("name") or selected.get("original_name") or refined),
                "description": selected.get("overview", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def get_book_title(item: object) -> str:
    if isinstance(item, dict) and "volumeInfo" in item and "title" in item["volumeInfo"]:
        return str(item["volumeInfo"]["title"])

    if isinstance(item, str):
        return item

    return ""

def fetch_book_metadata(title: str, author: str | None = None) -> dict[str, str]:
    try:
        refined = _refine_query(title)
        req_url = f"{GOOGLE_BOOKS_API_URL}?q={requests.utils.quote(refined)}"

        if author:
            req_url += f"+inauthor:{author}"

        res = requests.get(req_url, timeout=30).json()
        items = res.get("items", [])

        if items:
            best_match = process.extractOne(
                query=title, choices=items, processor=get_book_title, scorer=fuzz.WRatio
            )
            selected = best_match[0] if best_match else items[0]
            joined_authors = ", ".join(
                selected.get("volumeInfo", {}).get("authors", [])
            )
            return {
                "title": _clean_title(selected.get("volumeInfo", {}).get("title", refined)),
                "author": joined_authors,
                "description": selected.get("volumeInfo", {}).get("description", ""),
                "year": selected.get("volumeInfo", {}).get("publishedDate", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_metadata(
    media_type: str, title: str, year: int | None = None, author: str | None = None
) -> dict[str, str]:
    metadata = {}

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
