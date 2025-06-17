import os
from typing import Any
from fastapi import FastAPI, File, UploadFile, Depends, Form
from dotenv import load_dotenv
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from models.response import ErrorResponse

from app.auth import authorize
from services.ocr import extract_text_from_image
from services.classifier import MediaItem, extract_title_with_llm
from services.metadata import fetch_metadata

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
)

app = FastAPI()


@app.get("/")
async def check() -> dict[str, str]:
    return {"message": "Hello World"}


@app.post("/extract")
async def extract_info(
    file: UploadFile | None = File(None),
    query: str | None = Form(None),
    _auth: None = Depends(authorize),
) -> Any:
    if file is None and (query is None or query == ""):
        return JSONResponse(
            status_code=400,
            content={"error": "Either 'file' or 'query' must be provided."},
        )

    # Extraction
    full_text = ""

    if file is not None:
        extracted_info = await extract_text_from_image(file)

        if isinstance(extracted_info, ErrorResponse):
            return JSONResponse(status_code=500, content=extracted_info)

        full_text = extracted_info["text"]

    if query:
        full_text = f"{query} {full_text}".strip()

    # Classification
    llm_result = extract_title_with_llm(full_text)

    if isinstance(llm_result, ErrorResponse):
        return JSONResponse(status_code=500, content=llm_result)

    # Metadata Lookup
    metadatas: list[dict[str, str]] = []
    for item_data in llm_result:
        try:
            media_item = MediaItem.model_validate(item_data)

            # Now media_item is definitely a MediaItem instance, use dot notation
            metadata = fetch_metadata(
                media_type=media_item.type,
                title=media_item.title,
                # Commenting because LLM is not always returning the right info
                # year=media_item.year
                # author=media_item.author,
            )
            if metadata.get("title"):
                metadatas.append(metadata)

        except ValidationError as e:
            print(f"Skipping invalid item: {item_data} due to validation error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred processing item: {item_data}: {e}")

    return [
        {
            "title": metadata.get("title", ""),
            "type": metadata.get("type", ""),
            "author": metadata.get("author", ""),
            "year": metadata.get("year", ""),
            "description": metadata.get("description", ""),
        }
        for metadata in metadatas
    ]
