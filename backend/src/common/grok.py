"""Grok/xAI API client using xai-sdk."""
import os
import logging
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel
from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import x_search

from .config import CLIENT_TIMEOUT, MODEL
from .utils import load_env
from .save_session import get_session

log = logging.getLogger(__name__)

# Load .env BEFORE creating client
load_env()

# Global client for call_grok (used by strategies.py)
client = Client(
    api_key=os.getenv("XAI_API_KEY"),
    timeout=3600,
)


def call_grok(user_prompt: str, system_prompt: str = "", model: str = "grok-4-1-fast-reasoning", is_reasoning=True, max_tokens=512, response_model: Optional[BaseModel] = None) -> Union[str, BaseModel]:
    """Call Grok API with prompt."""
    if is_reasoning:
        chat = client.chat.create(model=model, max_tokens=max_tokens)
    else:
        chat = client.chat.create(model=model, max_tokens=max_tokens)
    chat.append(system(system_prompt))
    chat.append(user(user_prompt))
    
    if response_model:
        _, rm_response = chat.parse(response_model)
        return rm_response
    else:
        return chat.sample().content
    
def get_client(timeout: int = CLIENT_TIMEOUT) -> Client:
    """Get xAI SDK client."""
    api_key = os.getenv("XAI_API_KEY") or os.getenv("OFFLINE_XAI_API_KEY", "")
    if not api_key:
        raise ValueError("XAI_API_KEY environment variable not set")
    return Client(api_key=api_key, timeout=timeout)


def chat_completion(prompt: str, system: str = "", model: str = MODEL, step: str = "chat") -> str | None:
    """Simple chat completion. Returns response text or None on error."""
    try:
        client = get_client()
        chat = client.chat.create(model=model)
        if system:
            chat.append(user(system))
        chat.append(user(prompt))
        response = chat.sample().content
        get_session().log(step, prompt, response, model=model)
        return response
    except Exception as e:
        log.error(f"chat_completion error: {e}")
        return None


def analyze_pdf(pdf_path: str | Path, prompt: str, model: str = MODEL, step: str = "analyze_resume") -> str | None:
    """Analyze a PDF with Grok using Files API. Returns None on error."""
    client = get_client()
    uploaded = None
    try:
        uploaded = client.files.upload(Path(pdf_path).read_bytes(), filename=Path(pdf_path).name)
        chat = client.chat.create(model=model)
        chat.append(user(prompt, system(uploaded.id)))
        response = chat.sample().content
        get_session().log(step, prompt, response, model=model, filename=Path(pdf_path).name)
        return response
    except Exception as e:
        log.error(f"analyze_pdf error: {e}")
        return None
    finally:
        if uploaded:
            try:
                client.files.delete(uploaded.id)
            except Exception:
                pass  # Ignore cleanup errors


def analyze_image(image_path: str | Path, prompt: str, model: str = MODEL, timeout: int = CLIENT_TIMEOUT) -> str | None:
    """Analyze an image with Grok using Files API. Returns None on error."""
    client = get_client(timeout)
    uploaded = None
    try:
        uploaded = client.files.upload(Path(image_path).read_bytes(), filename=Path(image_path).name)
        chat = client.chat.create(model=model)
        chat.append(user(prompt, system(uploaded.id)))
        return chat.sample().content
    except Exception as e:
        log.error(f"analyze_image error: {e}")
        return None
    finally:
        if uploaded:
            try:
                client.files.delete(uploaded.id)
            except Exception:
                pass


def search_x(handle: str, prompt: str, model: str = MODEL) -> str | None:
    """Search X profile using Grok with x_search tool. Returns None on error."""
    try:
        client = get_client()
        chat = client.chat.create(
            model=model,
            tools=[x_search(allowed_x_handles=[handle], enable_image_understanding=True)],
        )
        chat.append(user(prompt))
        response = chat.sample().content
        get_session().log("search_x_profile", prompt, response, model=model, handle=handle)
        return response
    except Exception as e:
        log.error(f"search_x error for @{handle}: {e}")
        return None
    
