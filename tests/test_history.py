import json
import pytest
from datetime import datetime
from core.history import load_history, save_history, is_analyzed, add_record, get_all_records
from core.models import HistoryRecord


def make_record(video_id="vid1"):
    return HistoryRecord(
        video_id=video_id, url=f"https://tiktok.com/@u/video/{video_id}",
        caption="Test", source="favorites",
        author_username="devuser", author_display_name="Dev",
        like_count=100, comment_count=5, share_count=2, play_count=500,
        analyzed_date=datetime.utcnow().isoformat(),
        tool_count=3, run_id="run-001",
    )


def test_load_history_returns_empty_when_missing(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    assert load_history() == {}


def test_add_and_retrieve_record(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    rec = make_record("vid42")
    add_record(rec)
    history = load_history()
    assert "vid42" in history
    assert history["vid42"].author_username == "devuser"


def test_is_analyzed_returns_false_when_missing(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    assert is_analyzed("nonexistent") is False


def test_is_analyzed_returns_true_after_add(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    add_record(make_record("vid99"))
    assert is_analyzed("vid99") is True


def test_get_all_records(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    add_record(make_record("v1"))
    add_record(make_record("v2"))
    records = get_all_records()
    assert len(records) == 2


def test_add_record_overwrites_existing(tmp_dir, monkeypatch):
    monkeypatch.chdir(tmp_dir)
    (tmp_dir / "output").mkdir()
    rec = make_record("v1")
    add_record(rec)
    updated = make_record("v1")
    updated.tool_count = 99
    add_record(updated)
    assert load_history()["v1"].tool_count == 99
