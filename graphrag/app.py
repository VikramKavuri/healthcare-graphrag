"""FastAPI application exposing the Healthcare GraphRAG engine.

Routes are grouped under ``/api``. When the bundled static frontend is present
(``public/``), it is served at the root for a one-command local experience; in
production on Vercel the static assets are served by the CDN and this function
handles only ``/api/*``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .dataset import TABLE_NAMES, get_table, load_dataset
from .graph import get_graph, patient_graph_facts, patient_subgraph_nodes
from .llm import build_context, extractive_answer, generate_answer
from .reasoning import reasoning_subgraph_nodes
from .retrieval import get_index
from .schemas import AskRequest, AskResponse, Meta, Metrics, Patient
from .viz import LEGEND, serialize_subgraph

SUGGESTED_QUESTIONS = [
    "Which Life Plan goals are at risk, and what evidence supports that?",
    "What anxiety, mood, or participation concerns appear in the daily notes?",
    "What support strategies and interventions are in place for this patient?",
    "What medication, dose, or appointment concerns are documented?",
    "What risks or incidents have been recorded for this patient?",
    "What progress and setbacks are noted in the recent daily notes?",
]

# Frontend assets live at <repo>/public.
_PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


def _metrics() -> Metrics:
    graph = get_graph()
    return Metrics(
        patients=len(get_table("patients")),
        graph_nodes=graph.number_of_nodes(),
        graph_edges=graph.number_of_edges(),
        document_chunks=len(get_table("document_chunks")),
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.app_name} API",
        description="Graph-augmented retrieval over synthetic healthcare records.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "llm_enabled": settings.llm_enabled,
            "model": settings.llm_model if settings.llm_enabled else None,
        }

    @app.get("/api/meta", response_model=Meta)
    def meta() -> Meta:
        return Meta(
            app_name=settings.app_name,
            tagline=settings.app_tagline,
            llm_enabled=settings.llm_enabled,
            model=settings.llm_model,
            metrics=_metrics(),
            suggested_questions=SUGGESTED_QUESTIONS,
            legend=LEGEND,
            tables=list(TABLE_NAMES),
        )

    @app.get("/api/patients", response_model=List[Patient])
    def patients() -> List[Patient]:
        result = []
        for row in get_table("patients"):
            first = str(row.get("first_name") or "").strip()
            last = str(row.get("last_name") or "").strip()
            result.append(
                Patient(
                    id=str(row.get("patient_id")),
                    name=f"{first} {last}".strip(),
                    diagnosis=str(row.get("primary_diagnosis") or ""),
                    residence=str(row.get("residential_site") or ""),
                )
            )
        return result

    @app.get("/api/graph")
    def graph(patient_id: str = "all") -> dict:
        g = get_graph()
        nodes = patient_subgraph_nodes(g, patient_id)
        return serialize_subgraph(g, nodes)

    @app.post("/api/ask", response_model=AskResponse)
    def ask(request: AskRequest) -> AskResponse:
        tables = load_dataset()
        g = get_graph()

        chunks = get_index().search(request.question, request.patient_id, request.top_k)
        graph_facts = patient_graph_facts(g, request.patient_id)
        context = build_context(graph_facts, chunks)

        answer, llm_error = generate_answer(request.question, context)
        if answer is None:
            mode = "extractive"
            answer = extractive_answer(
                question=request.question,
                graph_facts=graph_facts,
                chunks=chunks,
                insights=get_table("bottleneck_insights"),
                patient_id=request.patient_id,
                llm_error=llm_error or "",
            )
        else:
            mode = "llm"

        nodes = reasoning_subgraph_nodes(g, request.patient_id, chunks, tables)
        return AskResponse(
            answer=answer,
            mode=mode,
            llm_error=llm_error if mode == "extractive" else None,
            graph_facts=graph_facts,
            evidence=chunks,
            reasoning_graph=serialize_subgraph(g, nodes),
        )

    @app.get("/api/tables/{name}")
    def table(name: str) -> dict:
        if name not in TABLE_NAMES:
            raise HTTPException(status_code=404, detail=f"Unknown table: {name}")
        rows = get_table(name)
        columns = list(rows[0].keys()) if rows else []
        return {"name": name, "columns": columns, "rows": rows}

    # Serve the static frontend for local development (Vercel serves it via CDN).
    if _PUBLIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_PUBLIC_DIR), html=True), name="static")

    return app


app = create_app()
