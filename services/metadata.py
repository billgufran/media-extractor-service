import os
import requests
from rapidfuzz import fuzz, process
import re


def _clean_title(text: str) -> str:
    """Remove parenthetical info like ' (film)' from a title."""
    return re.sub(r"\s*\([^\)]*\)$", "", text).strip()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
TMDB_API_URL = "https://api.themoviedb.org/3"


def resolve_title_with_wikipedia(title: str, media_type: str) -> str:
    """Use the Wikipedia search API to get the most likely canonical title."""
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
        res = requests.get("https://en.wikipedia.org/w/api.php", params=params).json()
        items = res.get("query", {}).get("search", [])
        if not items:
            return title
        candidate_titles = [item.get("title", "") for item in items]
        best_match = process.extractOne(title, candidate_titles, scorer=fuzz.ratio)
        chosen = best_match[0] if best_match else candidate_titles[0]
        return _clean_title(chosen)
    except Exception:
        return title


def fetch_movie_metadata(title: str, year: int | None = None):
    try:
        refined = resolve_title_with_wikipedia(title, "movie")
        req_url = (
            f"{TMDB_API_URL}/search/movie?api_key={TMDB_API_KEY}&query={refined}"
        )

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url).json()
        items = res.get("results", [])

        if items:
            selected = items[0]
            return {
                "title": selected.get("title", refined),
                "description": selected.get("overview", ""),
                "year": selected.get("release_date", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_tv_metadata(title: str, year: int | None = None):
    try:
        refined = resolve_title_with_wikipedia(title, "tv")
        req_url = f"{TMDB_API_URL}/search/tv?api_key={TMDB_API_KEY}&query={refined}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url).json()
        items = res.get("results", [])

        if items:
            selected = items[0]
            return {
                "title": selected.get("name", refined),
                "description": selected.get("overview", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_book_metadata(title: str, author: str | None = None):
    try:
        refined = resolve_title_with_wikipedia(title, "book")
        req_url = f"{GOOGLE_BOOKS_API_URL}?q={refined}"

        if author:
            req_url += f"+inauthor:{author}"

        res = requests.get(req_url).json()
        items = res.get("items", [])

        if items:
            selected = items[0]
            joined_authors = ", ".join(
                selected.get("volumeInfo", {}).get("authors", [])
            )
            return {
                "title": selected.get("volumeInfo", {}).get("title", refined),
                "author": joined_authors,
                "description": selected.get("volumeInfo", {}).get(
                    "description", ""
                ),
                "year": selected.get("volumeInfo", {}).get("publishedDate", ""),
            }
        return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_metadata(
    media_type: str, title: str, year: int | None = None, author: str | None = None
):
    metadata = {}

    if media_type == "movie":
        metadata = fetch_movie_metadata(title, year)
    elif media_type == "tv":
        metadata = fetch_tv_metadata(title, year)
    elif media_type == "book":
        metadata = fetch_book_metadata(title, author)

    # print("metadata", metadata)

    metadata_title = metadata.get("title")
    resolved_title = metadata_title if metadata_title is not None else title

    return {
        **metadata,
        "title": resolved_title,
        "type": media_type,
        "description": metadata.get("description", ""),
    }
