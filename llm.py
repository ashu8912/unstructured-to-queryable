import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Confirm the current free Flash id in Google AI Studio (run list_models.py).
MODEL = "gemini-flash-latest"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
