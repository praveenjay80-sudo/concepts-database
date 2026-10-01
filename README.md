# Concepts Database

A browsable atlas of 12,868 concepts across 15 domains (Physics, Biology, Chemistry,
Computation, Finance, Healthcare, Life Sciences, Mathematics, Engineering, History,
Law, Comedy, Libations, Construction, Music), pulled from the public read API of
[fock.space](https://fock.space).

## Features

- **Hierarchy browser** — DOMAIN → FIELD → CONCEPT → COMPONENT, grouped by universe.
- **Explain** — each concept's own plain-language and technical lenses, full article
  (with clickable cross-references), and typed related-concept links (part of,
  grounded in, instance of, caused, analogous to, contradicts).
- **Reading list generator** — on-demand, LLM-generated structured reading list per
  concept (Foundational → Research Frontier), with a model picker across current
  OpenRouter models. Results are cached to disk after first generation.

## Data

Source: [fock.space](https://fock.space)'s public read API (`api.fock.space`), pulled
in full via a rate-limited crawl respecting its `429` backoff. No published license
was found on fock.space at pull time (`/terms`, `/license` 404) — the API description
says "Read freely," but that is not a redistribution license. Treat this deployment
as a personal/research use of that data, not a guaranteed-reusable dataset, until
reuse terms are confirmed with the fock.space operator.

## Running locally

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-v1-...
uvicorn main:app --reload
```

## Deploy

Procfile is set up for Railway (`uvicorn main:app --host 0.0.0.0 --port $PORT`).
Set `OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`) as environment variables.
