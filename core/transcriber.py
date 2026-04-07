from __future__ import annotations
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from .models import VideoRecord, TranscriptMetadata

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")


def _load_cached_transcript(video_id: str, transcripts_dir: Path) -> Optional[str]:
    txt_file = transcripts_dir / f"{video_id}.txt"
    if txt_file.exists():
        return txt_file.read_text()
    return None


def _download_and_transcribe(video: VideoRecord, transcripts_dir: Path, cookies_file: Path) -> str:
    from faster_whisper import WhisperModel

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / f"{video.video_id}.mp3"
        cmd = [
            "yt-dlp",
            "-x", "--audio-format", "mp3",
            "--cookies", str(cookies_file),
            "-o", str(audio_path.with_suffix("")),
            "--quiet",
            video.url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr[:200]}")

        model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        segments, info = model.transcribe(str(audio_path), beam_size=5)
        transcript_text = " ".join(seg.text.strip() for seg in segments)

        meta = TranscriptMetadata(
            video_id=video.video_id, url=video.url, caption=video.caption,
            hashtags=video.hashtags, source=video.source,
            author_username=video.author_username,
            author_display_name=video.author_display_name,
            like_count=video.like_count, comment_count=video.comment_count,
            share_count=video.share_count, play_count=video.play_count,
            posted_date=video.posted_date,
            transcription_date=datetime.now(timezone.utc).isoformat(),
            whisper_model=WHISPER_MODEL,
            duration_seconds=info.duration if hasattr(info, "duration") else None,
            word_count=len(transcript_text.split()),
        )
        meta_file = transcripts_dir / f"{video.video_id}.json"
        meta_file.write_text(json.dumps(meta.model_dump(), indent=2))

        return transcript_text


def get_transcript(video: VideoRecord, transcripts_dir: Path, cookies_file: Path) -> Optional[str]:
    cached = _load_cached_transcript(video.video_id, transcripts_dir)
    if cached is not None:
        return cached
    try:
        transcript = _download_and_transcribe(video, transcripts_dir, cookies_file)
        transcripts_dir.mkdir(parents=True, exist_ok=True)
        txt_file = transcripts_dir / f"{video.video_id}.txt"
        txt_file.write_text(transcript)
        return transcript
    except Exception:
        return None
