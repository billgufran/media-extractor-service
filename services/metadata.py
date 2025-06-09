import os
import requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
TMDB_API_URL = "https://api.themoviedb.org/3"


def fetch_movie_metadata(title: str, year: int | None = None):
    try:
        req_url = f"{TMDB_API_URL}/search/movie?api_key={TMDB_API_KEY}&query={title}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url).json()
        items = res.get("results", [])

        if items and items[0]:
            return {
                "title": items[0].get("title", title),
                "description": items[0].get("overview", ""),
                "year": items[0].get("release_date", ""),
            }
        else:
            return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_tv_metadata(title: str, year: int | None = None):
    try:
        req_url = f"{TMDB_API_URL}/search/tv?api_key={TMDB_API_KEY}&query={title}"

        if year:
            req_url += f"&year={year}"

        res = requests.get(req_url).json()
        items = res.get("results", [])

        if items and items[0]:
            return {
                "title": items[0].get("name", title),
                "description": items[0].get("overview", ""),
            }
        else:
            return {}

    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}


def fetch_book_metadata(title: str, author: str | None = None):
    try:
        req_url = f"{GOOGLE_BOOKS_API_URL}?q={title}"

        if author:
            req_url += f"+inauthor:{author}"

        res = requests.get(req_url).json()
        items = res.get("items", [])

        if items and items[0]:
            joined_authors = ", ".join(
                items[0].get("volumeInfo", {}).get("authors", [])
            )
            return {
                "title": items[0].get("volumeInfo", {}).get("title", title),
                "author": joined_authors,
                "description": items[0].get("volumeInfo", {}).get(
                    "description", ""
                ),
                "year": items[0].get("volumeInfo", {}).get("publishedDate", ""),
            }
        else:
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
