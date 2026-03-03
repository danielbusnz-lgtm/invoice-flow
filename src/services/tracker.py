"""Track which email message IDs have already been processed.

Stores a JSON file in the project data/ directory so the cron job
skips emails it has already seen on previous runs.
"""

import json
from pathlib import Path
from typing import Set

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TRACKER_FILE = DATA_DIR / "processed_emails.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_processed_ids() -> Set[str]:
    """Load the set of already-processed message IDs from disk."""
    _ensure_data_dir()
    if not TRACKER_FILE.exists():
        return set()
    try:
        data = json.loads(TRACKER_FILE.read_text())
        return set(data)
    except (json.JSONDecodeError, TypeError):
        return set()


def save_processed_ids(ids: Set[str]):
    """Write the full set of processed message IDs to disk."""
    _ensure_data_dir()
    TRACKER_FILE.write_text(json.dumps(sorted(ids), indent=2))


def mark_processed(message_id: str):
    """Add a single message ID to the processed set and save."""
    ids = load_processed_ids()
    ids.add(message_id)
    save_processed_ids(ids)


def is_processed(message_id: str) -> bool:
    """Check whether a message ID has already been processed."""
    return message_id in load_processed_ids()
