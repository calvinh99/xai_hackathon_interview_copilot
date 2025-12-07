"""Test Grok image understanding (Single & Sequence)."""
from pathlib import Path
import os
from src.common.grok import analyze_image, analyze_image_sequence

DATA_DIR = Path(__file__).parent.parent / "data"

def test_single_image():
    image_path = DATA_DIR / "random_pic.JPG"
    if not image_path.exists():
        print(f"⚠️ Single image not found: {image_path}")
        return

    print(f"\n--- Testing Single Image: {image_path.name} ---")
    response = analyze_image(image_path, "What do you see in this image? Describe the content.", timeout=120)
    print(f"Response:\n{response}\n")

def test_image_sequence():
    img1 = DATA_DIR / "hao_sequence_1.jpg"
    img2 = DATA_DIR / "hao_sequence_2.jpg"
    
    if not img1.exists() or not img2.exists():
        # Fallback to step1/step2 if hao_sequence not found
        img1_alt = DATA_DIR / "step1.jpg"
        img2_alt = DATA_DIR / "step2.jpg"
        if img1_alt.exists() and img2_alt.exists():
            img1, img2 = img1_alt, img2_alt
        else:
            print(f"\n⚠️ Sequence images not found.")
            print(f"   Expected: {img1} AND {img2}")
            print("   Please add two sequential images to run the causality test.")
            return

    print(f"\n--- Testing Image Sequence (Causality): {img1.name} -> {img2.name} ---")
    
    prompt = """
    I am showing you two images in chronological order.
    Image 1 is the initial state.
    Image 2 is the subsequent state.

    Please analyze these images and provide:
    1. Causal Analysis: What happened between Image 1 and Image 2? What caused the change?
    2. Prediction: Based on Image 2, what is likely to happen next (Image 3)?
    """
    
    # Use vision model explicitly if needed, but default MODEL in config usually works if it's multi-modal
    # Assuming 'grok-vision-beta' or similar is the default or passed via config.
    # We'll rely on the default model in grok.py or override if we knew the vision model name.
    # For now, using default.
    
    response = analyze_image_sequence([img1, img2], prompt, timeout=120)
    print(f"Response:\n{response}\n")

if __name__ == "__main__":
    test_single_image()
    test_image_sequence()

