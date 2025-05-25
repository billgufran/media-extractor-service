from fastapi import FastAPI, File, UploadFile, Depends
from dotenv import load_dotenv
import os
from pydantic import ValidationError
from fastapi.responses import JSONResponse
from models.response import ErrorResponse

from app.auth import authorize

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from services.ocr import extract_text_from_image
from services.classifier import MediaItem, extract_title_with_llm
from services.metadata import fetch_metadata

app = FastAPI()

@app.get("/")
async def check():
    return {"message": "Hello World"}

@app.post("/extract")
async def extract_info(file: UploadFile = File(...), _auth=Depends(authorize)):
    full_text = await extract_text_from_image(file)

    if "error" in full_text:
        return JSONResponse(status_code=500, content=full_text)

    llm_result = extract_title_with_llm(full_text["text"])

    if llm_result is None:
        return JSONResponse(status_code=500, content=llm_result)

    if isinstance(llm_result, ErrorResponse):
        return JSONResponse(status_code=500, content=llm_result)

    print("llm_result", llm_result)

    metadatas = []
    for item_data in llm_result:
      try:
        # Pydantic v2 way: parse a dictionary directly into the model
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

    return [{
        "title": metadata.get("title"),
        "type": metadata.get("type"),
        "author": metadata.get("author"),
        "year": metadata.get("year"),
        "description": metadata.get("description"),
    } for metadata in metadatas]
