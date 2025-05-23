import os
import base64
import requests
from fastapi import UploadFile

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY")
VISION_ENDPOINT = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}"

async def extract_text_from_image(file: UploadFile):
    try:
        content = await file.read()
        encoded_image = base64.b64encode(content).decode("utf-8")

        request_body = {
            "requests": [
                {
                    "image": {
                        "content": encoded_image
                    },
                    "features": [{"type": "TEXT_DETECTION"}]
                }
            ]
        }

        response = requests.post(VISION_ENDPOINT, json=request_body)
        result = response.json()

        text = result["responses"][0].get("fullTextAnnotation", {}).get("text", "")
        return {"text": text}
    except Exception as e:
        return {"error": f"OCR failed: {str(e)}"}
