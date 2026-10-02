"""HTTP API: analyze an upload into labeled blocks, then render the APA document."""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError
from starlette.concurrency import run_in_threadpool

from .ai_classifier import ai_available
from .classifier import classify
from .limits import MAX_BLOCKS, MAX_UPLOAD_BYTES, RateLimiter, UploadError, validate_docx
from .models import AnalyzeResponse, LabelAssignment, RenderOptions
from .parser import parse_docx
from .renderer import render_docx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("apa")

app = FastAPI(title="APA Formatter", docs_url=None, redoc_url=None)

analyze_limiter = RateLimiter(int(os.environ.get("ANALYZE_PER_HOUR", "20")), 3600)
render_limiter = RateLimiter(int(os.environ.get("RENDER_PER_HOUR", "60")), 3600)
_labels_adapter = TypeAdapter(list[LabelAssignment])
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and os.environ.get("TRUST_PROXY", "1") == "1":
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        validate_docx(data)
    except UploadError as exc:
        raise HTTPException(400, str(exc)) from exc
    return data


def _parse(data: bytes):
    try:
        parsed = parse_docx(data)
    except Exception as exc:  # malformed XML, unsupported parts, ...
        log.info("Could not parse upload: %s", type(exc).__name__)
        raise HTTPException(400, "We could not read this document. Try re-saving it in Word as .docx.") from exc
    if len(parsed.blocks) > MAX_BLOCKS:
        raise HTTPException(400, "This document is too long for the free tool (about 60 pages maximum).")
    return parsed


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "ai": ai_available()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request, file: UploadFile = File(...)) -> AnalyzeResponse:
    if not analyze_limiter.allow(_client_key(request)):
        raise HTTPException(429, "You have reached the hourly limit. Please try again later.")
    data = await _read_upload(file)
    parsed = _parse(data)
    ai_used, warnings = await run_in_threadpool(classify, parsed.blocks)
    return AnalyzeResponse(blocks=parsed.blocks, ai_used=ai_used, warnings=warnings)


@app.post("/api/render")
async def render(
    request: Request,
    file: UploadFile = File(...),
    labels: str = Form(...),
    options: str = Form("{}"),
) -> Response:
    if not render_limiter.allow(_client_key(request)):
        raise HTTPException(429, "You have reached the hourly limit. Please try again later.")
    try:
        assignments = _labels_adapter.validate_json(labels)
        render_options = RenderOptions.model_validate(json.loads(options))
    except (ValidationError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "Invalid labels or options.") from exc

    data = await _read_upload(file)
    parsed = _parse(data)
    by_index = {a.index: a.label for a in assignments}
    if set(by_index) != {b.index for b in parsed.blocks}:
        raise HTTPException(409, "The labels do not match this document. Please analyze it again.")
    for block in parsed.blocks:
        block.label = by_index[block.index]

    output = await run_in_threadpool(render_docx, parsed, render_options)
    stem = re.sub(r"[^A-Za-z0-9 _.-]+", "", pathlib.Path(file.filename or "paper").stem).strip() or "paper"
    return Response(
        content=output,
        media_type=DOCX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{stem} (APA).docx"', "Cache-Control": "no-store"},
    )


_static = pathlib.Path(os.environ.get("STATIC_DIR", pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="static")
