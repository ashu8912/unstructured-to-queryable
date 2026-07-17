import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from schema import Receipt

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-flash-latest"   # confirm the current free Flash id in AI Studio

def extract_receipt(file_bytes: bytes, mime_type: str) -> Receipt:
    resp = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            "Extract the receipt fields. Use YYYY-MM-DD for the date. "
            "Return null for any field you can't find.",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Receipt,
        ),
    )
    return Receipt.model_validate_json(resp.text)