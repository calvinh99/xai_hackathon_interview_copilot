"""Grok/xAI API client."""
import os
import httpx

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = "https://api.x.ai/v1"


async def call_grok(prompt: str, system: str = "") -> str:
    """Call Grok API with prompt."""
    # TODO: implement
    return ""
