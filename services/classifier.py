# todo: type safe
import os
import requests
import json
from pydantic import BaseModel
from typing import Literal, Any, Optional

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemma-3n-e4b-it:free"

class MediaItem(BaseModel):
    type: Literal["movie", "book"]  # Only allow "movie" or "book"
    title: str  # Exact title extracted from LLM output

class ErrorResponse:
    error: str
    raw: Optional[Any]

def extract_title_with_llm(text: str):
    try:
        prompt = f"""
            You are given OCR-extracted text from an image. Your task is to:

            1. Identify all **movie** or **book** titles mentioned.
            2. Extract each title **exactly** as it appears (including correct casing and punctuation).
            3. Classify each title as either `"movie"` or `"book"` based on context.
            4. If a title could be both (e.g. *The Lord of the Rings*), use surrounding context to make your best guess.
            5. Return the result as a **JSON array** in this exact format:

            [
            {{
                "type": "movie" | "book",
                "title": "<exact title>"
            }}
            ]

            Begin with this text:

            {text}
            """
        system_msg = "You are a helpful assistant that extracts movie or book titles from unstructured text and returns a clean JSON array of type/title pairs."

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": system_msg,
                },
                {"role": "user", "content": prompt},
            ],
        }

        res = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        res_json = res.json()
        content = res_json["choices"][0]["message"]["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": f"Invalid JSON response: {content}", "raw": content}

    except Exception as e:
        return {"error": f"LLM error: {str(e)}"}
