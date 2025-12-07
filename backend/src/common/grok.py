"""Grok/xAI API client using xai-sdk."""
import os
from pathlib import Path
from xai_sdk import Client
from xai_sdk.chat import user, system as sys_msg, file
from xai_sdk.tools import x_search
from .config import CLIENT_TIMEOUT, MODEL
from .utils import load_env

# Load .env on import
load_env()


def get_client(timeout: int = CLIENT_TIMEOUT) -> Client:
    """Get xAI SDK client."""
    api_key = os.getenv("XAI_API_KEY") or os.getenv("OFFLINE_XAI_API_KEY", "")
    if not api_key:
        raise ValueError("XAI_API_KEY environment variable not set")
    return Client(api_key=api_key, timeout=timeout)


def chat_completion(prompt: str, system: str = "", model: str = MODEL) -> str:
    """Simple chat completion. Returns response text."""
    client = get_client()
    chat = client.chat.create(model=model)
    if system:
        chat.append(sys_msg(system))
    chat.append(user(prompt))
    return chat.sample().content


def analyze_pdf(pdf_path: str | Path, prompt: str, model: str = MODEL) -> str:
    """Analyze a PDF with Grok using Files API."""
    client = get_client()
    uploaded = client.files.upload(Path(pdf_path).read_bytes(), filename=Path(pdf_path).name)
    try:
        chat = client.chat.create(model=model)
        chat.append(user(prompt, file(uploaded.id)))
        return chat.sample().content
    finally:
        client.files.delete(uploaded.id)


def analyze_image(image_path: str | Path, prompt: str, model: str = MODEL, timeout: int = CLIENT_TIMEOUT) -> str:
    """Analyze an image with Grok using Files API."""
    client = get_client(timeout)
    uploaded = client.files.upload(Path(image_path).read_bytes(), filename=Path(image_path).name)
    try:
        chat = client.chat.create(model=model)
        chat.append(user(prompt, file(uploaded.id)))
        return chat.sample().content
    finally:
        client.files.delete(uploaded.id)


def search_x(handle: str, prompt: str, model: str = MODEL) -> str:
    """Search X profile using Grok with x_search tool."""
    client = get_client()
    chat = client.chat.create(
        model=model,
        tools=[x_search(allowed_x_handles=[handle], enable_image_understanding=True)],
    )
    chat.append(user(prompt))
    return chat.sample().content
