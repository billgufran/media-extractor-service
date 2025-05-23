from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from services.ocr import extract_text_from_image
from services.classifier import extract_title_with_llm
from services.metadata import fetch_metadata

app = FastAPI()

@app.post("/extract")
async def extract_info(file: UploadFile = File(...)):
    full_text = await extract_text_from_image(file)
    if "error" in full_text:
        return JSONResponse(status_code=500, content=full_text)

    llm_result = extract_title_with_llm(full_text["text"])
    if "error" in llm_result:
        return JSONResponse(status_code=500, content=llm_result)

    metadata = fetch_metadata(llm_result["type"], llm_result["title"])

    return {
        "title": llm_result["title"],
        "type": llm_result["type"],
        "raw_text": full_text["text"],
        "metadata": metadata
    }
