from __future__ import annotations
import json
from pathlib import Path
from .models import ExtractedTool, VideoRecord, RankedTool, ToolSource

CATEGORY_MULTIPLIERS = {
    "ai_model": 1.3,
    "cli": 1.3,
    "extension": 1.3,
    "workflow": 0.8,
    "hardware": 0.8,
}


def compute_score(mention_count: int, in_both: bool, category: str) -> float:
    score = float(mention_count)
    if in_both:
        score *= 1.5
    score *= CATEGORY_MULTIPLIERS.get(category, 1.0)
    return round(score, 2)


def aggregate(extractions_dir: Path, videos: list[VideoRecord]) -> list[RankedTool]:
    source_map = {v.video_id: v.source for v in videos}
    author_map = {v.video_id: v.author_username for v in videos}

    tool_registry: dict[str, dict] = {}

    if not extractions_dir.exists():
        return []

    for extraction_file in extractions_dir.glob("*.json"):
        if extraction_file.name.endswith("_analysis.json"):
            continue
        video_id = extraction_file.stem
        try:
            tools = [ExtractedTool(**t) for t in json.loads(extraction_file.read_text())]
        except Exception:
            continue

        src = source_map.get(video_id, "liked")
        author = author_map.get(video_id, "unknown")

        for tool in tools:
            key = tool.tool.lower()
            if key not in tool_registry:
                tool_registry[key] = {
                    "tool": tool,
                    "sources": [],
                    "in_favorites": False,
                    "in_liked": False,
                }
            entry = tool_registry[key]
            entry["sources"].append(
                ToolSource(video_id=video_id, author_username=author, source=src)
            )
            if src in ("favorites", "both"):
                entry["in_favorites"] = True
            if src in ("liked", "both"):
                entry["in_liked"] = True

    ranked = []
    for entry in tool_registry.values():
        tool = entry["tool"]
        in_both = entry["in_favorites"] and entry["in_liked"]
        score = compute_score(len(entry["sources"]), in_both, tool.category)
        ranked.append(RankedTool(
            tool=tool.tool,
            category=tool.category,
            description=tool.description,
            install_command=tool.install_command,
            url=tool.url,
            score=score,
            mention_count=len(entry["sources"]),
            sources=entry["sources"],
        ))

    ranked.sort(key=lambda t: t.score, reverse=True)
    return ranked
