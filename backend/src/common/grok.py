"""Grok/xAI API client."""
import os
from xai_sdk import Client
from xai_sdk.chat import user, image
from xai_sdk.chat import user, system

from pydantic import BaseModel
from typing import Optional, Union


client = Client(
    api_key=os.getenv("XAI_API_KEY"),
    timeout=3600, # Override default timeout with longer timeout for reasoning models
)

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = "https://api.x.ai/v1"


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
