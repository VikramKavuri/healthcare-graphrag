# Architecture

Healthcare GraphRAG is a graph-augmented retrieval system delivered as a Vercel
serverless API plus a static single-page frontend. This document explains the
design and the trade-offs behind it.

## Goals

1. **Grounded, auditable answers.** Care-team review needs to see the evidence,
   not just a conclusion. Every answer carries the subgraph and chunks used.
2. **Always-on demo.** The system must return a useful answer with no external
   dependencies, and transparently upgrade to Groq-generated answers when a key
   is present.
3. **Serverless-friendly.** Fast cold starts, a small function bundle, and no
   stateful infrastructure (no database, no model server).

## Request flow

```
question + patient_id + top_k
        │
        ▼
  retrieval.py ── TF-IDF over document chunks ──► ranked evidence chunks
        │
        ▼
  graph.py ────── patient neighbourhood ─────────► structured graph facts
        │
        ▼
  llm.py ──┬── GROQ_API_KEY set ──────► Groq model (grounded, structured answer)
           └── otherwise / on error ───► extractive engine (deterministic)
        │
        ▼
  reasoning.py ── map evidence back to graph ────► answer-traceability subgraph
        │
        ▼
  viz.py ──────── serialize for vis-network ─────► { nodes, edges }
```

## Components

| Module          | Responsibility                                                            |
| --------------- | ------------------------------------------------------------------------- |
| `dataset.py`    | Load the committed `dataset.json` snapshot (stdlib only, cached).         |
| `graph.py`      | Build a `MultiDiGraph` of clinical entities; expose facts and subgraphs.  |
| `retrieval.py`  | Pure-Python TF-IDF index with cosine similarity over document chunks.     |
| `reasoning.py`  | Select the subgraph of nodes that explains an answer.                     |
| `llm.py`        | Groq client (official SDK) and the deterministic extractive fallback.     |
| `viz.py`        | Node styling and vis-network serialization (the visual source of truth).  |
| `schemas.py`    | Pydantic models for typed, validated API I/O.                             |
| `app.py`        | FastAPI routes; serves the static frontend during local development.      |

## Key design decisions

### Data is a build-time snapshot, not a runtime dependency

The source spreadsheets in `data/` are converted to `graphrag/dataset.json` by
`scripts/prepare_data.py`. The serverless runtime reads only the JSON snapshot
using the standard library. This keeps **pandas, openpyxl, scikit-learn, scipy,
and numpy out of the deployed function** — smaller bundle, faster cold starts,
and a clean separation between "prepare data" and "serve data".

### Retrieval is pure-Python TF-IDF

The chunk corpus is small (tens of rows), so a hand-rolled TF-IDF + cosine
similarity index is both fast enough and dependency-free. It indexes the chunk
body plus its summary and section name for better recall. This replaces the
original scikit-learn dependency entirely.

### Graceful LLM degradation

`llm.generate_answer` returns `(None, reason)` when no key is configured or the
API call fails, and the pipeline falls back to `extractive_answer`, which
assembles a grounded response from bottleneck insights, graph facts, and
retrieved evidence. The deployed demo therefore works whether or not a key is
set, and the response always reports which engine produced the answer.

### The graph drives both retrieval context and the UI

`viz.py` is the single source of truth for node colours/shapes, consumed by both
the API (`/api/meta` legend) and the frontend, so the legend and the rendered
graph can never drift apart.

## Frontend

A dependency-light single-page app (`public/`) using vanilla JS and
[vis-network](https://visjs.github.io/vis-network/) (from CDN) for graph
rendering. It calls the JSON API, renders Markdown answers with a small,
HTML-escaping renderer, and visualizes both the full patient graph and the
per-answer traceability graph. No build step.

## Deployment

`vercel.json` maps `/api/*` to the single Python function (`api/index.py`, which
exports the ASGI `app`) and ships the `graphrag/` package (including the dataset)
via `includeFiles`. The static frontend in `public/` is served by Vercel's CDN.
`.vercelignore` keeps virtual environments, source spreadsheets, tests, and dev
tooling out of the upload.

## Extending

- **Real data / scale:** replace the JSON snapshot with a database-backed loader
  and swap the TF-IDF index for a vector store + embeddings; the `retrieval` and
  `dataset` interfaces are the seams to change.
- **Multimodal:** the document model already carries page references, so an
  image/PDF pipeline can attach to the chunk schema without graph changes.
