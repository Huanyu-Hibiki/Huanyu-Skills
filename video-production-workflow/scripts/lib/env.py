"""Load the shared .env file from the Skill root."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


SKILL_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = SKILL_ROOT / ".env"


def load_skill_env() -> Path:
    """Load local values without overwriting explicitly exported variables."""
    load_dotenv(ENV_FILE, override=False)
    return ENV_FILE


load_skill_env()
