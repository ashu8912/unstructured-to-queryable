import os
import time

from google import genai
from google.genai import errors as genai_errors
from dotenv import load_dotenv

load_dotenv()

# Primary model (override with GEMINI_MODEL). Confirm ids via list_models.py.
MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

# Extra models tried, in order, when the primary is rate-limited (429). Lighter
# models have separate quota, so this spreads load on the free tier.
FALLBACK_MODELS = [
    m.strip() for m in os.environ.get(
        "GEMINI_FALLBACK_MODELS", "gemini-2.0-flash,gemini-2.0-flash-lite"
    ).split(",") if m.strip()
]

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# HTTP codes worth retrying: rate limits and transient server errors.
_RETRYABLE = {429, 500, 502, 503, 504}


class ModelUnavailable(Exception):
    """Raised when the model can't be reached after retries. Carries a
    user-friendly message plus the underlying error for optional detail."""

    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.user_message = message
        self.original = original


def generate(*, model: str | None = None, contents, config, retries: int = 3):
    """Call the model with backoff, falling back to other models on rate limits.

    Tries the primary model (with exponential backoff on transient errors); if it
    stays rate-limited, moves on to the fallback models. Raises ModelUnavailable
    with a friendly message if every option fails.
    """
    models = [model or MODEL] + [m for m in FALLBACK_MODELS if m != (model or MODEL)]
    last_code: int | None = None
    last_exc: Exception | None = None

    for current in models:
        for attempt in range(retries + 1):
            try:
                return client.models.generate_content(
                    model=current, contents=contents, config=config)
            except genai_errors.APIError as e:
                last_exc, last_code = e, getattr(e, "code", None)
                if last_code == 429:
                    break  # exhausted for this model — try the next one
                if last_code in _RETRYABLE and attempt < retries:
                    time.sleep(1.5 * (2 ** attempt))  # 1.5s, 3s, 6s
                    continue
                raise ModelUnavailable(_friendly(last_code), e) from e
            except Exception as e:  # network / unexpected
                last_exc = e
                if attempt < retries:
                    time.sleep(1.5 * (2 ** attempt))
                    continue
                raise ModelUnavailable(
                    "Couldn't reach the AI service. Check your connection and try again.",
                    e) from e

    raise ModelUnavailable(_friendly(last_code), last_exc)


def _friendly(code: int | None) -> str:
    if code == 503:
        return ("The AI model is busy right now — this is usually temporary. "
                "Please try again in a few seconds.")
    if code == 429:
        return ("Rate limit reached on the free tier. "
                "Wait a moment before trying again.")
    if code in (401, 403):
        return "The AI service rejected the request (check the API key)."
    if code in (500, 502, 504):
        return "The AI service had a temporary error. Please try again."
    return "The AI service is unavailable right now. Please try again shortly."
