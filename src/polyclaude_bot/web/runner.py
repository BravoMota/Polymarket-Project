"""Subprocess runner for the CLI commands, with SSE streaming.

Design:
    POST /api/run/{command}   → registers a RunJob, returns its id.
    GET  /api/run/stream/{id} → actually spawns the subprocess and streams
                                stdout/stderr to the browser as SSE events.

Putting the subprocess lifecycle inside the stream handler keeps everything
on one event loop (avoids TestClient quirks and is simpler under uvicorn:
the loop that opened the pipe is the same one that reads it).
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

ALLOWED_COMMANDS: tuple[str, ...] = (
    "scan",
    "decide",
    "paper-run",
    "export-shortlist",
    "report",
)

# After each command finishes, which panels should the UI refresh?
REFRESH_TARGETS: dict[str, tuple[str, ...]] = {
    "scan": (),
    "decide": (),
    "paper-run": (),
    "export-shortlist": ("shortlist", "delta"),
    "report": (),
}


@dataclass
class RunJob:
    id: str
    command: str
    args: list[str]
    started: bool = False


_jobs: dict[str, RunJob] = {}


def _venv_python() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    if os.name == "nt":
        candidate = repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = repo_root / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_job(job_id: str) -> RunJob | None:
    return _jobs.get(job_id)


async def start_job(command: str, args: list[str] | None = None) -> RunJob:
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"command not allowed: {command}")
    job = RunJob(id=uuid.uuid4().hex, command=command, args=list(args or []))
    _jobs[job.id] = job
    return job


def _sse_event(data: str, *, event: str | None = None) -> str:
    lines = [f"event: {event}"] if event else []
    for line in data.splitlines() or [""]:
        lines.append(f"data: {line}")
    lines.append("")  # blank line terminates the event
    lines.append("")
    return "\n".join(lines)


async def stream_job(job: RunJob) -> AsyncIterator[str]:
    """Spawn the subprocess and stream its output to the caller as SSE."""
    if job.started:
        yield _sse_event("job already consumed", event="done")
        return
    job.started = True

    python = _venv_python()
    cmd = [str(python), "-m", "polyclaude_bot.cli", job.command, *job.args]
    yield _sse_event("$ " + " ".join(cmd), event="log")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=_repo_root(),
        )
    except OSError as exc:
        yield _sse_event(f"[runner error] {exc}", event="log")
        yield _sse_event("exit_code=1 refresh=", event="done")
        return

    assert process.stdout is not None
    try:
        async for raw in process.stdout:
            decoded = raw.decode("utf-8", errors="replace").rstrip("\n")
            if decoded:
                yield _sse_event(decoded, event="log")
    except asyncio.CancelledError:
        process.terminate()
        raise

    exit_code = await process.wait()
    refresh = ",".join(REFRESH_TARGETS.get(job.command, ()))
    yield _sse_event(f"exit_code={exit_code} refresh={refresh}", event="done")
