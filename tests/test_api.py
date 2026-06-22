"""Integration tests for the FastAPI surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from graphrag.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "llm_enabled" in body


def test_meta(client):
    body = client.get("/api/meta").json()
    assert body["metrics"]["patients"] > 0
    assert body["suggested_questions"]
    assert body["legend"]
    assert "patients" in body["tables"]


def test_patients(client):
    patients = client.get("/api/patients").json()
    assert patients
    assert {"id", "name", "diagnosis", "residence"} <= set(patients[0])


def test_graph(client):
    pid = client.get("/api/patients").json()[0]["id"]
    body = client.get("/api/graph", params={"patient_id": pid}).json()
    assert body["nodes"] and body["edges"]
    assert pid in {n["id"] for n in body["nodes"]}


def test_ask_returns_grounded_answer(client):
    pid = client.get("/api/patients").json()[0]["id"]
    body = client.post(
        "/api/ask",
        json={"question": "Which goals are at risk?", "patient_id": pid, "top_k": 5},
    ).json()
    assert body["mode"] in {"llm", "extractive"}
    assert body["answer"]
    assert "graph_facts" in body
    assert {"nodes", "edges"} <= set(body["reasoning_graph"])


def test_ask_validates_input(client):
    res = client.post("/api/ask", json={"question": "", "patient_id": "all"})
    assert res.status_code == 422


def test_tables_roundtrip(client):
    body = client.get("/api/tables/patients").json()
    assert body["columns"] and body["rows"]


def test_unknown_table_404(client):
    assert client.get("/api/tables/does_not_exist").status_code == 404
