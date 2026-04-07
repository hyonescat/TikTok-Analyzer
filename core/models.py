from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel


class VideoRecord(BaseModel):
    video_id: str
    url: str
    caption: str
    hashtags: list[str]
    source: Literal["favorites", "liked", "both"]
    author_username: str
    author_display_name: str
    like_count: int
    comment_count: int
    share_count: int
    play_count: int
    video_duration: Optional[int] = None
    posted_date: Optional[str] = None


class TranscriptMetadata(BaseModel):
    video_id: str
    url: str
    caption: str
    hashtags: list[str]
    source: str
    author_username: str
    author_display_name: str
    like_count: int
    comment_count: int
    share_count: int
    play_count: int
    posted_date: Optional[str] = None
    transcription_date: str
    whisper_model: str
    duration_seconds: Optional[float] = None
    word_count: int


class ExtractedTool(BaseModel):
    tool: str
    category: Literal["extension", "repo", "service", "cli", "framework", "ai_model", "workflow", "hardware"]
    description: str
    install_command: Optional[str] = None
    url: Optional[str] = None


class VideoAnalysis(BaseModel):
    video_id: str
    technologies: list[str] = []
    extensions: list[str] = []
    modules: list[str] = []
    ai_components: list[str] = []
    ai_names: list[str] = []


class ToolSource(BaseModel):
    video_id: str
    author_username: str
    source: str


class RankedTool(BaseModel):
    tool: str
    category: str
    description: str
    install_command: Optional[str] = None
    url: Optional[str] = None
    score: float
    mention_count: int
    sources: list[ToolSource] = []


class HistoryRecord(BaseModel):
    video_id: str
    url: str
    caption: str
    source: str
    author_username: str
    author_display_name: str
    like_count: int
    comment_count: int
    share_count: int
    play_count: int
    posted_date: Optional[str] = None
    analyzed_date: str
    tool_count: int
    run_id: str


class RunConfig(BaseModel):
    favorites: int = 50
    liked: int = 50
    favorites_only: bool = False
    dry_run: bool = False
    reprocess: Optional[str] = None
    rebuild_output: bool = False
