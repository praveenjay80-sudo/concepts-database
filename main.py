import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

APP_DIR = Path(__file__).parent

DEFAULT_MODEL = "google/gemini-3.8-flash"
ALLOWED_MODELS = {
    "anthropic/claude-sonnet-5.5", "anthropic/claude-opus-4.8", "anthropic/claude-haiku-4.5",
    "openai/gpt-5.6-sol", "openai/gpt-5.5",
    "google/gemini-3.8-flash", "google/gemini-3.5-flash",
    "x-ai/grok-4.7",
    "deepseek/deepseek-v3.2", "meta-llama/llama-4-maverick",
}

DETAIL_PATH = APP_DIR / "fock_detail.json"
DETAIL: dict = {}
if DETAIL_PATH.exists():
    with open(DETAIL_PATH, encoding="utf-8") as f:
        DETAIL = json.load(f)

app = FastAPI(title="Concepts Database")
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/api/concept/{concept_id}")
async def get_concept(concept_id: str):
    node = DETAIL.get(concept_id)
    if node is None:
        raise HTTPException(404, "Unknown concept id.")
    return node


@app.get("/api/models")
async def list_models():
    return {"default": DEFAULT_MODEL, "models": sorted(ALLOWED_MODELS)}


@app.get("/api/health")
async def health():
    return {"ok": True, "concepts_loaded": len(DETAIL)}


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith(".html") or path.endswith(".json"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


app.mount("/", StaticFiles(directory=str(APP_DIR / "public"), html=True), name="static")
