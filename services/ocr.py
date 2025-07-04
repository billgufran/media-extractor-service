import os
import base64
import requests
from fastapi import UploadFile

from models.response import ErrorResponse

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")
VISION_ENDPOINT = (
    f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"
)


async def extract_text_from_image(file: UploadFile) -> dict[str, str] | ErrorResponse:
    try:
        content = await file.read()
        encoded_image = base64.b64encode(content).decode("utf-8")

        request_body = {
            "requests": [
                {
                    "image": {"content": encoded_image},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }

        response = requests.post(VISION_ENDPOINT, json=request_body, timeout=30)

        if response.status_code != 200:
            return {
                "error": f"OCR failed with status code {response.status_code}: {response.text}"
            }

        result = response.json()

        if "error" in result:
            return ErrorResponse(error=result["error"], raw=result)

        extracted_text = (
            result["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        )

        return {"text": extracted_text}

    except Exception as e:
        return ErrorResponse(error=f"OCR failed: {str(e)}", raw=e)
