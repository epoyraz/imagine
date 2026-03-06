"""Lumenfall API client for image generation."""

import base64
from typing import Optional

from openai import OpenAI

from .config import (
    LUMENFALL_BASE_URL,
    get_api_key,
)


def create_client() -> OpenAI:
    """Create OpenAI client configured for Lumenfall."""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("LUMENFALL_API_KEY is not set")
    return OpenAI(
        api_key=api_key,
        base_url=LUMENFALL_BASE_URL,
    )


def generate_image(
    prompt: str,
    model: str = "gemini-3-pro-image",
    size: str = "1024x1024",
) -> bytes:
    """
    Generate an image from a text prompt via Lumenfall API.

    Returns raw image bytes (PNG).
    """
    client = create_client()
    response = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        response_format="b64_json",
    )
    b64_data = response.data[0].b64_json
    if not b64_data:
        raise ValueError("No image data in response")
    return base64.b64decode(b64_data)


def list_models() -> list[str]:
    """List available image generation models from Lumenfall."""
    client = create_client()
    models = client.models.list()
    # Filter to image models (Lumenfall may return various model types)
    return [m.id for m in models.data if hasattr(m, "id")]
