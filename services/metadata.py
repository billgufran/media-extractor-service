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


def resolve_title_with_wikipedia(title: str, media_type: str) -> str:
    """
    Attempts to resolve and return the canonical title of the given media using the Wikipedia search API.

    This function constructs a search query based on the title and media type (e.g., movie, tv, book),
    sends the query to Wikipedia, and selects the best matching title using fuzzy string matching.
    If no suitable match is found, returns the first canditate title. If an error occurs, the original input title is returned.

    Args:
        title (str): The original title to resolve.
        media_type (str): The type of media (e.g., "movie", "tv", "book").

    Returns:
        str: The resolved canonical title, or the original title if resolution fails.
    """
    try:
        media_hint = {
            "movie": "film",
            "tv": "television series",
            "book": "book",
        }.get(media_type, "")

        query = f"{title} {media_hint}".strip()
        params = {
            "action": "query",
            "list": "search",
            "format": "json",
            "srsearch": query,
        }
        res = requests.get(
            "https://en.wikipedia.org/w/api.php", params=params, timeout=30
        ).json()
        items = res.get("query", {}).get("search", [])
        if not items:
            return title
        candidate_titles = [item.get("title", "") for item in items]
        best_match = process.extractOne(title, candidate_titles, scorer=fuzz.ratio)
        chosen = best_match[0] if best_match else candidate_titles[0]
        return _clean_title(chosen)
    except Exception:
        return title


def fetch_movie_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = resolve_title_with_wikipedia(title, "movie")
        req_url = f"{TMDB_API_URL}/search/movie?api_key={TMDB_API_KEY}&query={refined}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url, timeout=30).json()
        items = res.get("results", [])

        if items:
            # might need to do fuzzy matching here as well
            selected = items[0]
            return {
                "title": selected.get("title", refined),
                "description": selected.get("overview", ""),
                "year": selected.get("release_date", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_tv_metadata(title: str, year: int | None = None) -> dict[str, str]:
    try:
        refined = resolve_title_with_wikipedia(title, "tv")
        req_url = f"{TMDB_API_URL}/search/tv?api_key={TMDB_API_KEY}&query={refined}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url, timeout=30).json()
        items = res.get("results", [])

        if items:
            # might need to do fuzzy matching here as well
            selected = items[0]
            return {
                "title": selected.get("name", refined),
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
        refined = resolve_title_with_wikipedia(title, "book")
        req_url = f"{GOOGLE_BOOKS_API_URL}?q={refined}"

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
                "title": selected.get("volumeInfo", {}).get("title", refined),
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
