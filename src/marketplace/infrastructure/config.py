"""Marketplace infrastructure configuration.

Reads environment variables and configures the application.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

MASTER_SEED = int(os.getenv("MASTER_SEED", "42"))
F4_DUPLICATE_RATE = float(os.getenv("F4_DUPLICATE_RATE", "0.0"))
F4_OOO_ENABLED = os.getenv("F4_OOO_ENABLED", "false").lower() == "true"
F4_OOO_MAX_LAG_SEC = int(os.getenv("F4_OOO_MAX_LAG_SEC", "21600"))
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "data/raw/events.jsonl")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "marketplace.events")
KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "false").lower() == "true"

_VALID_TOKENS_RAW = os.getenv("VALID_TOKENS", "token-seller-123,bearer-token-mercaandes-2026,test-token")
VALID_TOKENS = [t.strip() for t in _VALID_TOKENS_RAW.split(",") if t.strip()]

if not 0 <= F4_DUPLICATE_RATE <= 1:
    raise ValueError("F4_DUPLICATE_RATE must be between 0 and 1.")
if F4_OOO_MAX_LAG_SEC < 0 or F4_OOO_MAX_LAG_SEC > 21600:
    raise ValueError("F4_OOO_MAX_LAG_SEC must be between 0 and 21600.")
