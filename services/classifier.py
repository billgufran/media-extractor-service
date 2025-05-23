import os
import requests
import json
from pydantic import BaseModel
from typing import Literal, Any, NotRequired, Dict, TypedDict, Optional

from models.response import ErrorResponse

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemma-3n-e4b-it:free"

class MediaItem(BaseModel):
    type: Literal["movie", "book"]
    title: str
    author: Optional[str]
    year: Optional[int]

def extract_title_with_llm(text: str) -> list[MediaItem] | ErrorResponse:
    try:
        prompt = f"""
            You are given OCR-extracted text from an image. Your task is to:

            1. Identify all **movie** or **book** titles mentioned.
            2. Extract the **exact title** of the movie or book.
            3. Classify each title as either `"movie"` or `"book"` based on context.
            4. If the title is a movie, extract the year of release if known. Otherwise, omit the year.
            5. If the title is a book, extract the author if known. Otherwise, omit the author.
            6. If a title could be both (e.g. *The Lord of the Rings*), use surrounding context to make your best guess.
            7. Return the result as a raw text **JSON array** in this exact format without any surrounding text, explanations, or markdown formatting.:

            [
                {
                    "type": "movie" | "book",
                    "title": "<exact title>",
                    "author": "<exact author>",
                    "year": "<exact year>"
                }
            ]

            Begin with this text:

            {text}
            """

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        res_json = res.json()

        if "error" in res_json:
            return ErrorResponse(error=res_json["error"], raw=res_json)

        content = res_json["choices"][0]["message"]["content"]

        cleaned_content = content.strip("```").lstrip("json")

        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            return ErrorResponse(error="Invalid JSON response", raw=cleaned_content)

    except Exception as e:
        return ErrorResponse(error=f"LLM error: {str(e)}", raw=e)
