"""Test X search functionality."""
import os
import json
from pathlib import Path

# Load env
env_path = Path(__file__).parent / "src/offline/.env"
for line in env_path.read_text().splitlines():
    if line.strip() and not line.startswith("#") and "=" in line:
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"'))

from xai_sdk import Client
from xai_sdk.chat import user
from xai_sdk.tools import x_search

HANDLE = "scholarc1314"
SKILL = "CUDA"

SEARCH_X_PROMPT = """Search @{handle}'s X/Twitter posts for any content related to: {skill}

For each relevant post you find, classify it:
- "yes": Post demonstrates real expertise/deep knowledge (detailed technical insights, original work, teaching others)
- "could_be": Post shows interest but unclear depth (sharing articles, asking questions, surface-level comments)
- "no": Post suggests lack of knowledge (asking basic questions, admitting unfamiliarity)

Output ONLY valid JSON (no markdown):
{{"posts": [{{"url": "tweet URL", "content": "tweet text summary", "label": "yes/could_be/no"}}]}}

If no relevant posts found, output: {{"posts": []}}"""

def main():
    api_key = os.getenv("OFFLINE_XAI_API_KEY") or os.getenv("XAI_API_KEY")
    if not api_key:
        print("ERROR: No API key found")
        return

    client = Client(api_key=api_key)
    prompt = SEARCH_X_PROMPT.format(handle=HANDLE, skill=SKILL)

    print("=" * 60)
    print("RAW PROMPT:")
    print("=" * 60)
    print(prompt)
    print()

    print("=" * 60)
    print(f"Searching X @{HANDLE} for: {SKILL}")
    print("=" * 60)
    print("\n[Streaming...]")

    chat = client.chat.create(
        model="grok-4-1-fast",
        tools=[x_search(allowed_x_handles=[HANDLE], enable_image_understanding=True)],
    )
    chat.append(user(prompt))

    # Stream response
    response = None
    for response, chunk in chat.stream():
        if chunk.content:
            print(chunk.content, end="", flush=True)
        # Show tool calls
        if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
            for tc in chunk.tool_calls:
                print(f"\n[Tool: {tc}]", flush=True)
        # Show any other attributes
        if not chunk.content:
            print(f"[Chunk: {chunk}]", flush=True)

    print("\n")
    print("=" * 60)
    print("RAW RESPONSE:")
    print("=" * 60)
    print(response.content if response else "No response")
    print()

    # Parse
    print("=" * 60)
    print("PARSED OUTPUT:")
    print("=" * 60)
    text = (response.content if response else "").strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    try:
        data = json.loads(text.strip())
        posts = data.get("posts", [])
        print(f"Found {len(posts)} posts:")
        for i, p in enumerate(posts, 1):
            print(f"\n  [{i}] Label: {p.get('label', 'N/A')}")
            print(f"      URL: {p.get('url', 'N/A')}")
            print(f"      Content: {p.get('content', 'N/A')}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw text was: {text[:500]}")

if __name__ == "__main__":
    main()
