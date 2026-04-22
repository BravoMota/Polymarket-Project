"""FastAPI application wiring for the polyclaude-bot local UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from polyclaude_bot.web import env_store, handoff_reader, runner

WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

app = FastAPI(title="polyclaude", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


BUTTONS: list[dict[str, object]] = [
    {
        "command": "scan",
        "label": "Scan",
        "description": "Fetch raw markets → data/snapshots/",
        "dangerous": False,
    },
    {
        "command": "export-shortlist",
        "label": "Export Shortlist",
        "description": "Rank + write data/handoff/*.json",
        "dangerous": False,
    },
    {
        "command": "report",
        "label": "Report",
        "description": "Regenerate summary from ledger",
        "dangerous": False,
    },
    {
        "command": "decide",
        "label": "Decide",
        "description": "Calls the paid Anthropic API",
        "dangerous": True,
    },
    {
        "command": "paper-run",
        "label": "Paper Run",
        "description": "decide + report (paid Anthropic API)",
        "dangerous": True,
    },
]


def _dashboard_context() -> dict[str, object]:
    return {
        "shortlist": handoff_reader.load_shortlist(),
        "delta": handoff_reader.load_delta(),
        "decisions": handoff_reader.load_decisions(),
        "env_values": env_store.read_values(),
        "env_fields": env_store.EDITABLE_FIELDS,
        "buttons": BUTTONS,
        "env_saved": False,
        "env_error": None,
        "paste_error": None,
        "paste_saved": False,
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", _dashboard_context())


@app.get("/partials/shortlist", response_class=HTMLResponse)
async def partial_shortlist(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_shortlist.html",
        {"shortlist": handoff_reader.load_shortlist()},
    )


@app.get("/partials/delta", response_class=HTMLResponse)
async def partial_delta(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_delta.html",
        {"delta": handoff_reader.load_delta()},
    )


@app.get("/partials/decisions", response_class=HTMLResponse)
async def partial_decisions(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_decisions.html",
        {
            "decisions": handoff_reader.load_decisions(),
            "paste_error": None,
            "paste_saved": False,
        },
    )


@app.get("/partials/cowork-flow", response_class=HTMLResponse)
async def partial_cowork_flow(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "_cowork_flow.html", {})


@app.get("/api/cowork/prompt", response_class=PlainTextResponse)
async def api_cowork_prompt() -> PlainTextResponse:
    return PlainTextResponse(handoff_reader.load_prompt_text())


@app.get("/api/cowork/prompt-with-shortlist", response_class=PlainTextResponse)
async def api_cowork_prompt_with_shortlist() -> PlainTextResponse:
    return PlainTextResponse(handoff_reader.build_prompt_with_shortlist())


@app.get("/api/handoff/shortlist.json")
async def api_shortlist_json() -> Response:
    return Response(
        content=handoff_reader.load_shortlist_raw(),
        media_type="application/json",
    )


@app.post("/api/handoff/decisions", response_class=HTMLResponse)
async def api_save_decisions(request: Request) -> HTMLResponse:
    form = await request.form()
    text = str(form.get("text", ""))
    ok, err = handoff_reader.write_decisions(text)
    return templates.TemplateResponse(
        request,
        "_decisions.html",
        {
            "decisions": handoff_reader.load_decisions(),
            "paste_error": err,
            "paste_saved": ok,
        },
    )


@app.get("/partials/env", response_class=HTMLResponse)
async def partial_env(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "_env_form.html",
        {
            "env_values": env_store.read_values(),
            "env_fields": env_store.EDITABLE_FIELDS,
            "env_saved": False,
            "env_error": None,
        },
    )


@app.post("/api/env", response_class=HTMLResponse)
async def save_env(request: Request) -> HTMLResponse:
    form = await request.form()
    submitted = {
        field.key: str(form.get(field.key, "")).strip()
        for field in env_store.EDITABLE_FIELDS
    }
    try:
        env_store.write_values(submitted)
        env_error: str | None = None
        env_saved = True
        values = env_store.read_values()
    except env_store.EnvValidationError as exc:
        env_error = str(exc)
        env_saved = False
        values = submitted
    return templates.TemplateResponse(
        request,
        "_env_form.html",
        {
            "env_values": values,
            "env_fields": env_store.EDITABLE_FIELDS,
            "env_saved": env_saved,
            "env_error": env_error,
        },
    )


@app.post("/api/run/{command}", response_class=HTMLResponse)
async def api_run(request: Request, command: str) -> HTMLResponse:
    if command not in runner.ALLOWED_COMMANDS:
        raise HTTPException(status_code=400, detail="unknown command")
    job = await runner.start_job(command)
    return templates.TemplateResponse(
        request,
        "_run_output.html",
        {"job": job, "streaming": True},
    )


@app.get("/api/run/stream/{job_id}")
async def api_run_stream(job_id: str) -> StreamingResponse:
    job = runner.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return StreamingResponse(
        runner.stream_job(job),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
