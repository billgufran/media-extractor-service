import os
import requests

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

def fetch_metadata(media_type: str, title: str):
    try:
        if media_type == "movie":
            tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
            res = requests.get(tmdb_url).json()
            results = res.get("results", [])
            return results[0] if results else {}
        elif media_type == "book":
            params = {"q": title}
            res = requests.get(GOOGLE_BOOKS_API, params=params).json()
            items = res.get("items", [])
            return items[0] if items else {}
        else:
            return {}
    except Exception as e:
        return {"error": f"Metadata lookup failed: {str(e)}"}
