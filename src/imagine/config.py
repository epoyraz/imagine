"""Configuration for Imagine CLI."""

import os
from pathlib import Path
from typing import Optional

# Lumenfall API
LUMENFALL_BASE_URL = "https://api.lumenfall.ai/openai/v1"
LUMENFALL_API_KEY_ENV = "LUMENFALL_API_KEY"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"  # Some users might set this for Lumenfall

# Default model (from Lumenfall catalog)
DEFAULT_MODEL = "gemini-3-pro-image"
DEFAULT_SIZE = "1024x1024"

# Config file paths (cross-platform)
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "imagine"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_api_key() -> Optional[str]:
    """Get Lumenfall API key from environment."""
    return os.environ.get(LUMENFALL_API_KEY_ENV) or os.environ.get(OPENAI_API_KEY_ENV)


def validate_api_key() -> None:
    """Raise if API key is not configured."""
    key = get_api_key()
    if not key or not key.strip():
        raise SystemExit(
            "Error: LUMENFALL_API_KEY is not set.\n"
            "Get your API key at https://lumenfall.ai and run:\n"
            "  export LUMENFALL_API_KEY=lmnfl_your_key"
        )


def load_config() -> dict:
    """Load optional config from ~/.config/imagine/config.json."""
    config: dict = {"model": DEFAULT_MODEL, "size": DEFAULT_SIZE}
    config_path = CONFIG_DIR / "config.json"
    if not config_path.exists():
        return config
    try:
        import json
        with open(config_path) as f:
            data = json.load(f)
        if "model" in data:
            config["model"] = str(data["model"])
        if "size" in data:
            config["size"] = str(data["size"])
    except Exception:
        pass
    return config
