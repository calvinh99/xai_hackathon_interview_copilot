from pathlib import Path

def load_text(name: str, base_dir: Path) -> str | None:
    """
    Load baseline prompt text from baseline_prompts/<name>.txt if present.
    Returns None when the file is missing.
    """
    path = base_dir / f"{name}.txt"
    if not path.exists():
        return None
    return path.read_text()