from __future__ import annotations
import asyncio
import os
import random
from pathlib import Path
from typing import Optional
from .models import VideoRecord

RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "2.5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


def validate_cookies_file(cookies_file: Path) -> None:
    if not cookies_file.exists():
        raise FileNotFoundError(
            f"Cookie file not found: {cookies_file}\n"
            "Export cookies from Chrome using 'Get cookies.txt LOCALLY' extension\n"
            "and save to ./cookies/cookies.txt"
        )


def load_cookies_file(cookies_file: Path) -> str:
    validate_cookies_file(cookies_file)
    return cookies_file.read_text()


def deduplicate_videos(videos: list[VideoRecord]) -> list[VideoRecord]:
    seen: dict[str, VideoRecord] = {}
    for v in videos:
        if v.video_id not in seen:
            seen[v.video_id] = v
    return list(seen.values())


def merge_sources(favorites: list[VideoRecord], liked: list[VideoRecord]) -> list[VideoRecord]:
    registry: dict[str, VideoRecord] = {}
    for v in favorites:
        registry[v.video_id] = v.model_copy(update={"source": "favorites"})
    for v in liked:
        if v.video_id in registry:
            registry[v.video_id] = registry[v.video_id].model_copy(update={"source": "both"})
        else:
            registry[v.video_id] = v.model_copy(update={"source": "liked"})
    return list(registry.values())


def _parse_count(text: str) -> int:
    text = text.strip().upper().replace(",", "")
    if text.endswith("K"):
        return int(float(text[:-1]) * 1000)
    if text.endswith("M"):
        return int(float(text[:-1]) * 1_000_000)
    try:
        return int(text)
    except ValueError:
        return 0


def _parse_netscape_cookies(content: str) -> list[dict]:
    cookies = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _, path, secure, expires, name, value = parts[:7]
        # Playwright requires expires to be -1 (session) or a positive unix
        # timestamp in seconds. Chrome exports microseconds for some cookies;
        # cap anything > year 9999 (~32503680000s) down to -1 (session).
        try:
            exp = int(expires)
            if exp <= 0:
                exp = -1
            elif exp > 32503680000:  # microsecond-range value
                exp = exp // 1_000_000  # convert µs → s
                if exp > 32503680000:   # still absurd → treat as session
                    exp = -1
        except (ValueError, TypeError):
            exp = -1
        cookies.append({
            "name": name, "value": value,
            "domain": domain, "path": path,
            "secure": secure.upper() == "TRUE",
            "expires": exp,
        })
    return cookies


async def _collect_from_tab(page, tab_url: str, limit: int, emit_fn) -> list[VideoRecord]:
    """Scroll the given TikTok tab and collect up to `limit` video records."""
    await page.goto(tab_url, wait_until="networkidle")
    await asyncio.sleep(random.uniform(2, 4))

    videos: dict[str, VideoRecord] = {}
    retries = 0

    while len(videos) < limit:
        cards = await page.query_selector_all("div[data-e2e='user-post-item']")
        for card in cards:
            if len(videos) >= limit:
                break
            try:
                link = await card.query_selector("a")
                href = await link.get_attribute("href") if link else None
                if not href or "/video/" not in href:
                    continue
                video_id = href.split("/video/")[-1].split("?")[0]
                if video_id in videos:
                    continue

                caption_el = await card.query_selector("div[data-e2e='user-post-item-desc']")
                caption = (await caption_el.inner_text()).strip() if caption_el else ""

                like_el = await card.query_selector("strong[data-e2e='video-stats-like-count']")
                like_count = _parse_count(await like_el.inner_text() if like_el else "0")

                videos[video_id] = VideoRecord(
                    video_id=video_id,
                    url=f"https://www.tiktok.com{href}" if href.startswith("/") else href,
                    caption=caption,
                    hashtags=[w.lstrip("#") for w in caption.split() if w.startswith("#")],
                    source="favorites",
                    author_username=href.split("/@")[1].split("/")[0] if "/@" in href else "unknown",
                    author_display_name="",
                    like_count=like_count,
                    comment_count=0,
                    share_count=0,
                    play_count=0,
                )
                emit_fn("log", f"Collected video {video_id}: {caption[:50]}")
            except Exception:
                continue

        prev_count = len(videos)
        await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        await asyncio.sleep(random.uniform(RATE_LIMIT_DELAY, RATE_LIMIT_DELAY + 2.5))

        if len(videos) == prev_count:
            retries += 1
            if retries >= MAX_RETRIES:
                break
        else:
            retries = 0

    return list(videos.values())


async def collect_videos(
    cookies_file: Path,
    favorites_limit: int,
    liked_limit: int,
    favorites_only: bool,
    emit_fn,
    history_ids: set[str],
) -> list[VideoRecord]:
    from playwright.async_api import async_playwright

    validate_cookies_file(cookies_file)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(_parse_netscape_cookies(cookies_file.read_text()))
        page = await context.new_page()

        await page.goto("https://www.tiktok.com/", wait_until="networkidle")
        await asyncio.sleep(2)

        profile_url = "https://www.tiktok.com/profile"
        favorites: list[VideoRecord] = []
        liked: list[VideoRecord] = []

        if favorites_limit > 0:
            emit_fn("log", f"Collecting up to {favorites_limit} favorites...")
            favorites = await _collect_from_tab(page, f"{profile_url}?tab=favorites", favorites_limit, emit_fn)
            emit_fn("log", f"Collected {len(favorites)} favorites")

        if not favorites_only and liked_limit > 0:
            emit_fn("log", f"Collecting up to {liked_limit} liked videos...")
            liked = await _collect_from_tab(page, f"{profile_url}?tab=liked", liked_limit, emit_fn)
            emit_fn("log", f"Collected {len(liked)} liked videos")

        await browser.close()

    merged = merge_sources(favorites, liked)
    new_videos = [v for v in merged if v.video_id not in history_ids]
    emit_fn("log", f"{len(new_videos)} new videos (skipped {len(merged) - len(new_videos)} already analyzed)")
    return new_videos
