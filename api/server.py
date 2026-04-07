from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse
from core.models import RunConfig
from core.history import get_all_records

app = FastAPI(title="TikTok Analyzer API")

EXTRACTIONS_DIR = Path("extractions")

_state: dict[str, Any] = {
    "status": "idle",
    "process": None,
    "queue": None,
}


def get_output_dir() -> Path:
    return Path("output")


async def _spawn_analyze(config: RunConfig) -> None:
    _state["status"] = "running"
    _state["queue"] = asyncio.Queue()

    cmd = ["python", "analyze.py", "--json-output"]
    if config.favorites:
        cmd += ["--favorites", str(config.favorites)]
    if config.liked:
        cmd += ["--liked", str(config.liked)]
    if config.favorites_only:
        cmd.append("--favorites-only")
    if config.dry_run:
        cmd.append("--dry-run")
    if config.reprocess:
        cmd += ["--reprocess", config.reprocess]
    if config.rebuild_output:
        cmd.append("--rebuild-output")

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    _state["process"] = process

    async for raw_line in process.stdout:
        line = raw_line.decode().strip()
        if not line:
            continue
        try:
            event_obj = json.loads(line)
        except json.JSONDecodeError:
            event_obj = {"event": "log", "data": line}
        await _state["queue"].put(event_obj)

    await process.wait()
    final_event = "done" if process.returncode == 0 else "error"
    _state["status"] = final_event
    await _state["queue"].put({"event": final_event, "data": ""})


@app.post("/api/run")
async def start_run(config: RunConfig, background_tasks: BackgroundTasks):
    if _state["status"] == "running":
        raise HTTPException(status_code=409, detail="A run is already in progress")
    background_tasks.add_task(_spawn_analyze, config)
    return {"status": "started"}


@app.get("/api/progress")
async def progress():
    async def generate():
        if _state["queue"] is None:
            yield {"event": "error", "data": json.dumps("No active run")}
            return
        while True:
            try:
                event = await asyncio.wait_for(_state["queue"].get(), timeout=30)
                yield {"event": event["event"], "data": json.dumps(event["data"])}
                if event["event"] in ("done", "error"):
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": json.dumps("")}
    return EventSourceResponse(generate())


@app.get("/api/status")
async def status():
    return {"status": _state["status"]}


@app.get("/api/results")
async def results():
    results_file = get_output_dir() / "tools_ranked.json"
    if not results_file.exists():
        raise HTTPException(status_code=404, detail="No results yet. Run an analysis first.")
    return json.loads(results_file.read_text())


@app.get("/api/results/todo")
async def results_todo():
    todo_file = get_output_dir() / "todo_list.md"
    if not todo_file.exists():
        raise HTTPException(status_code=404, detail="No to-do list yet.")
    return PlainTextResponse(todo_file.read_text())


@app.post("/api/run/cancel")
async def cancel_run():
    proc = _state.get("process")
    if proc and _state["status"] == "running":
        proc.kill()
        _state["status"] = "idle"
        if _state["queue"]:
            await _state["queue"].put({"event": "error", "data": "Cancelled by user"})
    return {"status": "cancelled"}


@app.get("/api/history")
async def history():
    records = get_all_records()
    return [r.model_dump() for r in records]


@app.get("/api/analysis/{video_id}")
async def get_analysis(video_id: str):
    analysis_file = EXTRACTIONS_DIR / f"{video_id}_analysis.json"
    if not analysis_file.exists():
        raise HTTPException(status_code=404, detail="No analysis found for this video")
    return json.loads(analysis_file.read_text())


if __name__ == "__main__":
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)
