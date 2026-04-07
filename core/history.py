from __future__ import annotations
import json
from pathlib import Path
from .models import HistoryRecord

HISTORY_FILE = Path("output/history.json")


def load_history() -> dict[str, HistoryRecord]:
    if not HISTORY_FILE.exists():
        return {}
    data = json.loads(HISTORY_FILE.read_text())
    return {k: HistoryRecord(**v) for k, v in data.items()}


def save_history(history: dict[str, HistoryRecord]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps({k: v.model_dump() for k, v in history.items()}, indent=2)
    )


def is_analyzed(video_id: str) -> bool:
    return video_id in load_history()


def add_record(record: HistoryRecord) -> None:
    history = load_history()
    history[record.video_id] = record
    save_history(history)


def get_all_records() -> list[HistoryRecord]:
    return list(load_history().values())
