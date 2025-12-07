#!/usr/bin/env python3
"""
Demo script for calling the Podcast API endpoints.

This script demonstrates POST methods for generating a podcast using the Podcast API.
"""

import base64
import requests
from pydantic import BaseModel, Field
import os


class SamplingParams(BaseModel):
    max_new_tokens: int = Field(..., description="Maximum number of new tokens to generate")
    temperature: float = Field(..., description="Temperature")
    min_p: float = Field(..., description="Minimum probability")
    seed: int | None = Field(None, description="Seed")
    repetition_penalty: float = Field(1.0, description="Repetition penalty")

DEFAULT_SAMPLING_PARAMS = SamplingParams(
    max_new_tokens=4096, temperature=1.0, min_p=0.01, seed=191119, repetition_penalty=1.0
)


class Speaker(BaseModel):
    id: str = Field(..., description="Speaker ID")
    audio: str | None = Field(None, description="Audio Base64")
    voice: list[int] | str | None = Field(
        None,
        description="Voice - can be a list of ints or a base64 encoded audio or a file path. File path only for debugging.",
    )
    instructions: str = Field(
        "", max_length=16000, description="Instructions (max 16000 characters)"
    )


class Turn(BaseModel):
    speaker_id: str
    text: str


class GeneratePodcastModel(BaseModel):
    model: str = Field(..., description="Model name")
    speakers: list[Speaker] = Field(..., description="Personalities")
    sampling_params: SamplingParams = Field(
        DEFAULT_SAMPLING_PARAMS, description="Sampling parameters"
    )
    response_format: str = Field(..., description="Response format")
    script: list[Turn] | None = Field(..., description="Script")
    num_tts_blocks_history: int = Field(5, description="Number of TTS blocks history")


API_KEY = os.environ.get("XAI_API_KEY")
BASE_URL = "https://us-east-4.api.x.ai/voice-staging"
ENDPOINT = f"{BASE_URL}/api/v1/text-to-speech/generate-podcast"

MAX_INPUT_LENGTH = 4096
MAX_PROMPT_LENGTH = 4096


def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def podcast_request(model: GeneratePodcastModel, output_file: str = "output.mp3"):
    payload = model.model_dump()

    response = requests.post(ENDPOINT, json=payload, stream=True, headers={"Authorization": f"Bearer {API_KEY}"})

    if response.status_code == 200:
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Audio saved to {output_file}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")


def main():
    """
    Demo examples showing different use cases.
    """
    print("=" * 60)
    print("Podcast API Demo")
    print("=" * 60)

    print("\n📝 Simple Podcast request")
    print("-" * 60)
    podcast_request(
        GeneratePodcastModel(
            model="grok-voice",
            speakers=[
                Speaker(
                    id="Steve",
                    audio=file_to_base64("voices/steve-jobs.m4a"),
                    voice=None,
                    instructions="",
                ),
                Speaker(
                    id="Grant",
                    audio=file_to_base64("voices/grant.m4a"),
                    voice=None,
                    instructions="",
                ),
            ],
            script=[
                Turn(speaker_id="Steve", text="Hi Grant, how are you doing?"),
                Turn(
                    speaker_id="Grant",
                    text="Hey Steve, I'm doing great - let's learn some math! you ready?",
                ),
                Turn(speaker_id="Steve", text="I love microsoft"),
                Turn(
                    speaker_id="Grant",
                    text="Wonderful! Let's get started!",
                ),
                Turn(speaker_id="Steve", text="Great! Let's get started!"),
                Turn(speaker_id="Grant", text="Great! Let's get started!"),
                Turn(speaker_id="Steve", text="Great! Let's get started!"),
                Turn(speaker_id="Grant", text="Great! Let's get started!"),
                Turn(speaker_id="Steve", text="Great! Let's get started!"),
            ],
            num_tts_blocks_history=4,
            response_format="mp3",
            sampling_params=DEFAULT_SAMPLING_PARAMS,
        ),
        output_file="example1_podcast.mp3",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure to:")
        print("1. Update BASE_URL with your actual domain")
        print("2. Install requests: pip install requests")
        print("3. Ensure the API endpoint is accessible")
