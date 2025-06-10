import json
from pydantic import BaseModel
from typing import Literal, Optional
from langchain.schema import HumanMessage
from services.llm_client import llm

from models.response import ErrorResponse


class MediaItem(BaseModel):
    type: Literal["movie", "book" , "tv"]
    title: str
    author: Optional[str] = None
    year: Optional[int] = None

def extract_title_with_llm(text: str) -> list[MediaItem] | ErrorResponse:
    try:
        prompt = f"""
            You are given OCR-extracted text from an image. Your task is to:

            1. Identify all **movie**, **tv**, or **book** titles mentioned.
            2. Extract the **exact title** of the movie, tv, or book.
            3. Classify each title as either `"movie"`, `tv`, or `"book"` based on context.
            4. If the title is a movie or tv, extract the year of release if known. Otherwise, omit the year.
            5. If the title is a book, extract the author if known. Otherwise, omit the author.
            6. If a title could be both (e.g. *The Lord of the Rings*), use surrounding context to make your best guess.
            7. Return the result as a raw text **JSON array** in this exact format without any surrounding text, explanations, or markdown formatting:

            [
                {{
                    "type": "movie" | "tv" | "book",
                    "title": "<exact title>",
                    "author": "<exact author>",
                    "year": "<exact year>"
                }}
            ]

            Begin with this text:

            {text}
            """

        response = llm.invoke([HumanMessage(content=prompt)])

        content = getattr(response, "content", response)

        if not isinstance(content, str):
            content = str(content)

        cleaned_content = content.strip("`").lstrip("json").strip()

        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            return ErrorResponse(error="Invalid JSON response", raw=cleaned_content)

    except Exception as e:
        return ErrorResponse(error=f"LLM error: {str(e)}", raw=e)
