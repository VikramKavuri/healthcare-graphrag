"""Answer-traceability reasoning over the knowledge graph.

After retrieval, these helpers select the subgraph of nodes that explain an
answer: the patient, the evidence chunks mapped back to graph nodes, and the
clinically relevant goals/barriers/interventions around them. The result powers
the "Answer Traceability Graph" shown alongside each answer.
"""

from __future__ import annotations

from typing import List, Set

import networkx as nx

from .dataset import Dataset, Row

# Graph node types that carry clinical/progress meaning for traceability.
_CORE_LABELS = {"Goal", "Barrier", "Intervention", "SupportPlan", "IncidentRisk"}


def map_chunks_to_nodes(chunks: List[Row], tables: Dataset) -> Set[str]:
    """Map retrieved document chunks back to the graph nodes they came from."""
    nodes: Set[str] = set()
    if not chunks:
        return nodes

    doc_ids = {str(c.get("document_id")) for c in chunks if c.get("document_id") is not None}
    nodes.update(
        str(c.get("patient_id")) for c in chunks if c.get("patient_id") is not None
    )

    mappings = (
        ("daily_notes", "note_id"),
        ("incidents_and_risks", "incident_id"),
        ("life_plan_goals", "goal_id"),
        ("support_plans", "support_plan_id"),
    )
    for table_name, id_field in mappings:
        for row in tables.get(table_name, []):
            if str(row.get("document_id")) in doc_ids and row.get(id_field) is not None:
                nodes.add(str(row.get(id_field)))

    return nodes


def reasoning_subgraph_nodes(
    graph: nx.MultiDiGraph,
    patient_id: str,
    chunks: List[Row],
    tables: Dataset,
) -> Set[str]:
    """Build the node set for the answer-traceability subgraph."""
    nodes: Set[str] = set()

    if patient_id != "all" and patient_id in graph:
        nodes.add(patient_id)

    nodes.update(map_chunks_to_nodes(chunks, tables))

    if patient_id != "all" and patient_id in graph:
        for _, dst, _ in graph.out_edges(patient_id, data=True):
            label = graph.nodes[dst].get("label", "")
            if label in _CORE_LABELS:
                nodes.add(dst)

        # Expand one hop around the included clinical nodes to show how the
        # evidence connects (barriers/interventions and their owning goals).
        for node in list(nodes):
            if node not in graph:
                continue
            for _, dst, _ in graph.out_edges(node, data=True):
                if graph.nodes[dst].get("label") in {"Barrier", "Intervention"}:
                    nodes.add(dst)
            for src, _, _ in graph.in_edges(node, data=True):
                if graph.nodes[src].get("label") in {"Goal", "Intervention", "Patient"}:
                    nodes.add(src)

    return {node for node in nodes if node in graph}
