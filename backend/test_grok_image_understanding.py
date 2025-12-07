"""Test Grok image understanding."""
from pathlib import Path
from src.common.grok import analyze_image

IMAGE_PATH = Path(__file__).parent.parent / "data" / "random_pic.JPG"

if __name__ == "__main__":
    print(f"Analyzing image: {IMAGE_PATH}")
    response = analyze_image(IMAGE_PATH, "What do you see in this image? Describe the content.", timeout=120)
    print(f"\nResponse:\n{response}")
