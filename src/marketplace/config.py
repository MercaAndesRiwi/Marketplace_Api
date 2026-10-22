"""Configuración del productor de eventos marketplace."""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

MASTER_SEED = int(os.getenv("MASTER_SEED", "42"))
F4_DUPLICATE_RATE = float(os.getenv("F4_DUPLICATE_RATE", "0.0"))
F4_OOO_ENABLED = os.getenv("F4_OOO_ENABLED", "false").lower() == "true"
F4_OOO_MAX_LAG_SEC = int(os.getenv("F4_OOO_MAX_LAG_SEC", "21600"))
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "data/raw/events.jsonl")

if not 0 <= F4_DUPLICATE_RATE <= 1:
    raise ValueError("F4_DUPLICATE_RATE must be between 0 and 1.")
if F4_OOO_MAX_LAG_SEC < 0 or F4_OOO_MAX_LAG_SEC > 21600:
    raise ValueError("F4_OOO_MAX_LAG_SEC must be between 0 and 21600.")
