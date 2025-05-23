# services/llm.py

import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "google/gemma-3n-e4b-it:free"


def extract_title_with_llm(text: str):
    try:
        prompt = """
            You will be given text extracted from an image. Your task is to:

            1. Detect whether the text mentions some movies, books, or mix of both.
            2. Extract the **exact title** of the movie or book.
            3. Apply the correct type to the output.
            4. Output format should and always will be:
            [
                {
                "type": "movie" | "book",
                "title": "<title here>"
                }
            ]

            If you are unsure, or if the title is ambiguous because it is a movie and also a book (e.g. "The Lord of the Rings"), make your best guess based on context. The text start below:

            {text}
            """

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an assistant that extracts structured media information (movies or books) from noisy OCR text. Always return a valid JSON array of objects.",
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

        return eval(
            content
        )  # Optional: replace with `json.loads` with stricter validation
    except Exception as e:
        return {"error": f"LLM error: {str(e)}"}
