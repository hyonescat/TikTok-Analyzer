#!/usr/bin/env python3
"""
TikTok Analyzer CLI
Usage: python analyze.py [options]
When --json-output is set, all output is JSON lines (used by FastAPI server).
"""
from __future__ import annotations
import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRANSCRIPTS_DIR = Path("transcripts")
EXTRACTIONS_DIR = Path("extractions")
OUTPUT_DIR = Path("output")
LOGS_DIR = Path("logs")
COOKIES_FILE = Path("cookies/cookies.txt")
JSON_OUTPUT = "--json-output" in sys.argv


def emit(event: str, data) -> None:
    if JSON_OUTPUT:
        print(json.dumps({"event": event, "data": data}), flush=True)
    else:
        from rich.console import Console
        console = Console()
        if event == "log":
            console.print(f"[dim]{data}[/dim]")
        elif event == "transcript":
            console.print(f"[green]Transcript[/green] [{data.get('video_id', '')}]: {str(data.get('text', ''))[:80]}…")
        elif event == "analysis":
            ai = data.get("ai_names", [])
            console.print(f"[blue]Analysis[/blue] [{data.get('video_id', '')}]: AI={ai}")
        elif event == "done":
            console.print(f"[bold green]Done.[/bold green] {data}")
        elif event == "error":
            console.print(f"[bold red]Error:[/bold red] {data}")


def log(msg: str) -> None:
    emit("log", msg)


def save_failed_video(video_id: str, url: str, reason: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    failed_file = LOGS_DIR / "failed_videos.json"
    records = json.loads(failed_file.read_text()) if failed_file.exists() else []
    records.append({"video_id": video_id, "url": url, "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat()})
    failed_file.write_text(json.dumps(records, indent=2))


def save_llm_failure(video_id: str, error: str) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    failures_file = LOGS_DIR / "llm_failures.json"
    records = json.loads(failures_file.read_text()) if failures_file.exists() else []
    records.append({"video_id": video_id, "error": error, "timestamp": datetime.now(timezone.utc).isoformat()})
    failures_file.write_text(json.dumps(records, indent=2))


async def run(args: argparse.Namespace) -> None:
    from core.history import is_analyzed, add_record, get_all_records, load_history
    from core.collector import collect_videos
    from core.transcriber import get_transcript
    from core.extractor import extract_tools
    from core.analyzer import analyze_video
    from core.ranker import aggregate
    from core.models import HistoryRecord, VideoRecord

    run_id = str(uuid.uuid4())[:8]
    start = datetime.now(timezone.utc)

    for d in [TRANSCRIPTS_DIR, EXTRACTIONS_DIR, OUTPUT_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # --- Collect videos ---
    if args.rebuild_output:
        log("Rebuild mode: loading all history records")
        history = load_history()
        videos = [
            VideoRecord(
                video_id=r.video_id, url=r.url, caption=r.caption,
                hashtags=[], source=r.source,
                author_username=r.author_username,
                author_display_name=r.author_display_name,
                like_count=r.like_count, comment_count=r.comment_count,
                share_count=r.share_count, play_count=r.play_count,
                posted_date=r.posted_date,
            )
            for r in history.values()
        ]
    elif args.reprocess:
        history = load_history()
        if args.reprocess not in history:
            emit("error", f"Video {args.reprocess} not found in history")
            return
        rec = history[args.reprocess]
        videos = [VideoRecord(
            video_id=rec.video_id, url=rec.url, caption=rec.caption,
            hashtags=[], source=rec.source,
            author_username=rec.author_username, author_display_name=rec.author_display_name,
            like_count=rec.like_count, comment_count=rec.comment_count,
            share_count=rec.share_count, play_count=rec.play_count,
        )]
        for f in [(EXTRACTIONS_DIR / f"{args.reprocess}.json"), (EXTRACTIONS_DIR / f"{args.reprocess}_analysis.json")]:
            if f.exists():
                f.unlink()
    else:
        history_ids = {r.video_id for r in get_all_records()}
        if args.dry_run:
            log("Dry run: collecting video list only (no transcription or extraction)")
        videos = await collect_videos(
            cookies_file=COOKIES_FILE,
            favorites_limit=args.favorites if not args.favorites_only or args.favorites else 0,
            liked_limit=0 if args.favorites_only else args.liked,
            favorites_only=args.favorites_only,
            emit_fn=emit,
            history_ids=history_ids,
        )
        if args.dry_run:
            log(f"Dry run complete. Found {len(videos)} new videos.")
            emit("done", {"videos": len(videos), "tools": 0, "duration_seconds": 0})
            return

    # --- Transcribe + Extract ---
    processed = 0
    for i, video in enumerate(videos, 1):
        log(f"Processing video {i}/{len(videos)}: {video.video_id}")

        transcript = get_transcript(video, TRANSCRIPTS_DIR, COOKIES_FILE)
        if transcript is None:
            save_failed_video(video.video_id, video.url, "yt-dlp download failed")
            log(f"Skipping {video.video_id}: download failed")
            continue

        emit("transcript", {
            "video_id": video.video_id,
            "caption": video.caption,
            "source": video.source,
            "author_username": video.author_username,
            "like_count": video.like_count,
            "text": transcript,
        })

        try:
            tools = extract_tools(video, transcript, EXTRACTIONS_DIR)
        except Exception as e:
            save_llm_failure(video.video_id, str(e))
            log(f"Skipping LLM extraction for {video.video_id}: {e}")
            tools = []

        try:
            from core.models import VideoAnalysis
            analysis = analyze_video(video, transcript, EXTRACTIONS_DIR)
            emit("analysis", analysis.model_dump())
        except Exception as e:
            log(f"Structured analysis failed for {video.video_id}: {e}")
            from core.models import VideoAnalysis
            analysis = VideoAnalysis(video_id=video.video_id)

        add_record(HistoryRecord(
            video_id=video.video_id, url=video.url, caption=video.caption,
            source=video.source, author_username=video.author_username,
            author_display_name=video.author_display_name,
            like_count=video.like_count, comment_count=video.comment_count,
            share_count=video.share_count, play_count=video.play_count,
            posted_date=video.posted_date,
            analyzed_date=datetime.now(timezone.utc).isoformat(),
            tool_count=len(tools),
            run_id=run_id,
        ))
        processed += 1

    # --- Rank and output ---
    all_history = load_history()
    all_videos_for_ranking = [
        VideoRecord(
            video_id=r.video_id, url=r.url, caption=r.caption,
            hashtags=[], source=r.source,
            author_username=r.author_username, author_display_name=r.author_display_name,
            like_count=r.like_count, comment_count=r.comment_count,
            share_count=r.share_count, play_count=r.play_count,
        )
        for r in all_history.values()
    ]

    ranked = aggregate(EXTRACTIONS_DIR, all_videos_for_ranking)
    _write_outputs(ranked, processed)

    duration = (datetime.now(timezone.utc) - start).seconds
    emit("done", {"videos": processed, "tools": len(ranked), "duration_seconds": duration})


def _write_outputs(ranked: list, processed: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUT_DIR / "tools_ranked.json").write_text(
        json.dumps([r.model_dump() for r in ranked], indent=2)
    )

    CATEGORY_HEADERS = {
        "ai_model": "AI Models & Services",
        "cli": "CLI Tools",
        "extension": "VS Code / Cursor Extensions",
        "framework": "Frameworks & Libraries",
        "repo": "GitHub Repos",
        "service": "Services & Platforms",
        "workflow": "Workflows & Practices",
        "hardware": "Hardware",
    }
    CATEGORY_EMOJI = {
        "ai_model": "🤖", "cli": "🛠️", "extension": "🧩",
        "framework": "📦", "repo": "📂", "service": "☁️",
        "workflow": "⚙️", "hardware": "💻",
    }

    by_category: dict[str, list] = {}
    for tool in ranked:
        by_category.setdefault(tool.category, []).append(tool)

    lines = [
        "# Developer Setup To-Do List",
        f"Generated: {datetime.now().strftime('%Y-%m-%d')} | Videos analyzed: {processed} | Unique tools found: {len(ranked)}",
        "",
        "---",
        "",
    ]
    for cat, tools in sorted(by_category.items(), key=lambda x: -sum(t.score for t in x[1])):
        emoji = CATEGORY_EMOJI.get(cat, "📌")
        header = CATEGORY_HEADERS.get(cat, cat.title())
        lines.append(f"## {emoji} {header}")
        for t in tools:
            url_part = f" | [{t.url}]({t.url})" if t.url else ""
            cmd_part = f" | `{t.install_command}`" if t.install_command else ""
            authors = list({s.author_username for s in t.sources})[:3]
            lines.append(f"- [ ] **{t.tool}** — {t.description} (score: {t.score}){url_part}{cmd_part}")
            lines.append(f"  - Mentioned in: {t.mention_count} videos by {', '.join(authors)}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by TikTok Analyzer — running fully local on your machine*")
    (OUTPUT_DIR / "todo_list.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="TikTok Analyzer")
    parser.add_argument("--favorites", type=int, default=50)
    parser.add_argument("--liked", type=int, default=50)
    parser.add_argument("--favorites-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reprocess", type=str, default=None)
    parser.add_argument("--rebuild-output", action="store_true")
    parser.add_argument("--json-output", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
