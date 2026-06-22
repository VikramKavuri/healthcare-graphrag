"""Unit tests for the GraphRAG engine (dataset, graph, retrieval, answers)."""

from __future__ import annotations

from graphrag import config, llm
from graphrag.dataset import TABLE_NAMES, get_table, load_dataset
from graphrag.graph import build_graph, get_graph, patient_graph_facts, patient_subgraph_nodes
from graphrag.reasoning import reasoning_subgraph_nodes
from graphrag.retrieval import TfidfIndex, get_index
from graphrag.viz import serialize_subgraph


def _first_patient_id() -> str:
    return str(get_table("patients")[0]["patient_id"])


# ---------------------------------------------------------------- dataset


def test_dataset_loads_all_tables():
    data = load_dataset()
    assert set(TABLE_NAMES).issubset(data.keys())
    assert len(data["patients"]) > 0


# ---------------------------------------------------------------- graph


def test_graph_has_nodes_and_edges():
    graph = build_graph(load_dataset())
    assert graph.number_of_nodes() > 0
    assert graph.number_of_edges() > 0
    labels = {attrs.get("label") for _, attrs in graph.nodes(data=True)}
    assert "Patient" in labels and "Goal" in labels


def test_patient_facts_and_subgraph():
    graph = get_graph()
    pid = _first_patient_id()
    facts = patient_graph_facts(graph, pid)
    assert facts and all(pid in f or "-[" in f for f in facts)

    nodes = patient_subgraph_nodes(graph, pid)
    assert pid in nodes
    assert len(nodes) > 1


def test_all_patients_returns_empty_facts():
    assert patient_graph_facts(get_graph(), "all") == []


# ---------------------------------------------------------------- retrieval


def test_retrieval_ranks_relevant_chunks_first():
    index = get_index()
    results = index.search("anxiety before community outings", top_k=5)
    assert results
    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < s <= 1.0 for s in scores)


def test_retrieval_patient_scoping():
    pid = _first_patient_id()
    results = get_index().search("goal", patient_id=pid, top_k=10)
    assert all(str(r["patient_id"]) == pid for r in results)


def test_retrieval_handles_empty_corpus():
    assert TfidfIndex([]).search("anything") == []


# ---------------------------------------------------------------- reasoning + viz


def test_reasoning_subgraph_is_serialisable():
    graph = get_graph()
    pid = _first_patient_id()
    chunks = get_index().search("goal at risk", patient_id=pid, top_k=5)
    nodes = reasoning_subgraph_nodes(graph, pid, chunks, load_dataset())
    payload = serialize_subgraph(graph, nodes)
    assert pid in nodes
    assert {"nodes", "edges"} == set(payload)
    assert all({"id", "color", "shape", "type"} <= set(n) for n in payload["nodes"])


# ---------------------------------------------------------------- answers


def test_extractive_answer_contains_sections():
    pid = _first_patient_id()
    facts = patient_graph_facts(get_graph(), pid)
    chunks = get_index().search("medication", patient_id=pid, top_k=3)
    answer = llm.extractive_answer(
        question="What concerns are documented?",
        graph_facts=facts,
        chunks=chunks,
        insights=get_table("bottleneck_insights"),
        patient_id=pid,
    )
    assert "### Direct Answer" in answer


def test_generate_answer_without_key_returns_reason(monkeypatch):
    monkeypatch.setattr(llm, "settings", config.Settings(groq_api_key=None))
    answer, reason = llm.generate_answer("q", "context")
    assert answer is None
    assert reason
