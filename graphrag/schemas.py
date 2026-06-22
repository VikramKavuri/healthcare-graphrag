"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Body for ``POST /api/ask``."""

    question: str = Field(..., min_length=1, max_length=2000)
    patient_id: str = Field("all", description="Patient id, or 'all' for the whole cohort.")
    top_k: int = Field(8, ge=1, le=20, description="Number of document chunks to retrieve.")


class Patient(BaseModel):
    id: str
    name: str
    diagnosis: str
    residence: str


class GraphNode(BaseModel):
    id: str
    label: str
    title: str
    type: str
    color: str
    shape: str
    size: int


class GraphEdge(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    label: str

    model_config = {"populate_by_name": True}


class Graph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AskResponse(BaseModel):
    answer: str
    mode: str = Field(..., description="'llm' or 'extractive'.")
    llm_error: str | None = None
    graph_facts: list[str]
    evidence: list[dict[str, object]]
    reasoning_graph: Graph


class Metrics(BaseModel):
    patients: int
    graph_nodes: int
    graph_edges: int
    document_chunks: int


class Meta(BaseModel):
    app_name: str
    tagline: str
    llm_enabled: bool
    model: str
    metrics: Metrics
    suggested_questions: list[str]
    legend: list[dict[str, object]]
    tables: list[str]
