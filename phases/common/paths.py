from pathlib import Path

# Repository root (mutual-fund/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


def resolve_path(relative: str) -> Path:
    path = PROJECT_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
