import hashlib
import json
import os
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

APP_DIR = Path(__file__).parent
CACHE_DIR = APP_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-3.8-flash")

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


class ConceptRequest(BaseModel):
    id: str = ""
    name: str
    path: list[str] = []
    children: list[str] = []
    model: str = ""


def cache_path(kind: str, name: str) -> Path:
    h = hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:20]
    return CACHE_DIR / f"{kind}_{h}.json"


def extract_json(content: str):
    match = re.search(r"\[[\s\S]*\]|\{[\s\S]*\}", content)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


async def call_openrouter(prompt: str, max_tokens: int, model: str) -> str:
    if not OPENROUTER_API_KEY:
        raise HTTPException(500, "Server is not configured with an OpenRouter API key.")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
            },
        )
    if resp.status_code != 200:
        raise HTTPException(502, f"OpenRouter error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


READING_LIST_PROMPT = """You are an expert academic librarian. Generate an EXHAUSTIVE reading list for the concept: "{name}"

Context:
- Path in the atlas: {path}
- Related sub-concepts: {children}
- Summary: {summary}

Generate a structured reading list with these sections:
1. FOUNDATIONAL TEXTS (3-5 books) - The canonical texts every student must read
2. INTRODUCTORY (3-5 books/courses) - Accessible entry points for beginners
3. INTERMEDIATE (5-8 books) - Core textbooks for undergraduate/early graduate level
4. ADVANCED (5-8 books/papers) - Graduate-level and specialist texts
5. RESEARCH FRONTIER (3-5 seminal papers/recent works) - Cutting-edge and highly cited
6. CROSS-DISCIPLINARY (3-5 works) - Essential readings from adjacent fields
7. REFERENCE WORKS (2-4) - Handbooks, encyclopedias, companions
8. JOURNALS (3-5) - Top journals in the field
9. ONLINE RESOURCES (3-5) - Key websites, databases, lecture series

For each item, format as:
**[Title]** by [Author] ([Year])
Type: [Book/Textbook/Paper/Journal/Course/Website]
Level: [Foundational/Introductory/Intermediate/Advanced/Frontier]
Why: [1-2 sentence justification]

Be specific with real titles, real authors, real publication years. No placeholder text. If you are unsure about a specific title, omit it rather than guessing.

Return ONLY a structured JSON array, no other text:
[{{"section": "...", "title": "...", "author": "...", "year": "...", "type": "...", "level": "...", "why": "..."}}]"""


@app.get("/api/concept/{concept_id}")
async def get_concept(concept_id: str):
    node = DETAIL.get(concept_id)
    if node is None:
        raise HTTPException(404, "Unknown concept id.")
    return node


@app.post("/api/reading-list")
async def reading_list(req: ConceptRequest):
    model = req.model if req.model in ALLOWED_MODELS else DEFAULT_MODEL
    cf = cache_path("reading", req.name + "|" + (req.id or "") + "|" + model)
    if cf.exists():
        return json.loads(cf.read_text(encoding="utf-8"))

    summary = ""
    node = DETAIL.get(req.id) if req.id else None
    if node:
        summary = (node.get("lenses") or {}).get("tech") or (node.get("lenses") or {}).get("plain") or ""

    prompt = READING_LIST_PROMPT.format(
        name=req.name,
        path=" -> ".join(req.path) if req.path else req.name,
        children=", ".join(req.children) or "none",
        summary=summary or "none",
    )
    content = await call_openrouter(prompt, max_tokens=4000, model=model)
    items = extract_json(content)
    result = {"topic": req.name, "items": items or [], "raw": content, "model": model}
    cf.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result


@app.get("/api/models")
async def list_models():
    return {"default": DEFAULT_MODEL, "models": sorted(ALLOWED_MODELS)}


@app.get("/api/health")
async def health():
    return {"ok": True, "openrouter_configured": bool(OPENROUTER_API_KEY), "concepts_loaded": len(DETAIL)}


app.mount("/", StaticFiles(directory=str(APP_DIR / "public"), html=True), name="static")
