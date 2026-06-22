"""Build a patient-centered knowledge graph from the dataset tables.

The graph is a :class:`networkx.MultiDiGraph` whose nodes are clinical entities
(patients, goals, barriers, interventions, notes, plans, incidents, …) and whose
edges are typed relationships between them. It is the backbone of both the
graph-context retrieval and the answer-traceability visualisation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, List, Set

import networkx as nx

from .dataset import Dataset, Row, load_dataset

# Visual + semantic metadata for each node type, shared by the API and frontend.
NODE_TYPES = (
    "Patient",
    "Program",
    "Goal",
    "Barrier",
    "Intervention",
    "DailyNote",
    "SupportPlan",
    "IncidentRisk",
    "Appointment",
    "Medication",
    "CareTeamMember",
)


def _clean(value: object) -> str:
    """Render a cell value as a trimmed string, treating null-ish values as empty."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none"} else text


def build_graph(tables: Dataset) -> nx.MultiDiGraph:
    """Construct the knowledge graph from the dataset tables."""
    graph = nx.MultiDiGraph()

    def add_node(node_id: object, label: str, **attrs: object) -> None:
        node = _clean(node_id)
        if node:
            graph.add_node(node, label=label, **attrs)

    def add_edge(src: object, dst: object, relation: str) -> None:
        source, target = _clean(src), _clean(dst)
        if source and target:
            graph.add_edge(source, target, relation=relation)

    def rows(name: str) -> Iterable[Row]:
        return tables.get(name, [])

    for r in rows("patients"):
        name = f"{_clean(r.get('first_name'))} {_clean(r.get('last_name'))}".strip()
        add_node(
            r.get("patient_id"),
            "Patient",
            name=name,
            diagnosis=_clean(r.get("primary_diagnosis")),
            residence=_clean(r.get("residential_site")),
            details=(
                f"Diagnosis: {_clean(r.get('primary_diagnosis'))}\n"
                f"Residence: {_clean(r.get('residential_site'))}\n"
                f"Care Manager: {_clean(r.get('care_manager_name'))}"
            ),
        )

    for r in rows("care_programs"):
        add_node(
            r.get("program_id"),
            "Program",
            type=_clean(r.get("program_type")),
            site=_clean(r.get("program_site")),
            details=(
                f"Site: {_clean(r.get('program_site'))}\n"
                f"Frequency: {_clean(r.get('service_frequency'))}\n"
                f"Status: {_clean(r.get('program_status'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("program_id"), "ENROLLED_IN")

    for r in rows("life_plan_goals"):
        add_node(
            r.get("goal_id"),
            "Goal",
            category=_clean(r.get("goal_category")),
            description=_clean(r.get("goal_description")),
            status=_clean(r.get("goal_status")),
            priority=_clean(r.get("priority_level")),
            details=(
                f"Goal: {_clean(r.get('goal_description'))}\n"
                f"Outcome: {_clean(r.get('desired_outcome'))}\n"
                f"Status: {_clean(r.get('goal_status'))}\n"
                f"Priority: {_clean(r.get('priority_level'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("goal_id"), "HAS_GOAL")

    for r in rows("barriers"):
        add_node(
            r.get("barrier_id"),
            "Barrier",
            type=_clean(r.get("barrier_type")),
            description=_clean(r.get("barrier_description")),
            severity=_clean(r.get("severity_level")),
            frequency=_clean(r.get("frequency_count")),
            details=(
                f"Type: {_clean(r.get('barrier_type'))}\n"
                f"Severity: {_clean(r.get('severity_level'))}\n"
                f"Frequency: {_clean(r.get('frequency_count'))}\n"
                f"Description: {_clean(r.get('barrier_description'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("barrier_id"), "HAS_BARRIER")
        add_edge(r.get("related_goal_id"), r.get("barrier_id"), "BLOCKED_BY")

    for r in rows("interventions"):
        add_node(
            r.get("intervention_id"),
            "Intervention",
            type=_clean(r.get("intervention_type")),
            description=_clean(r.get("intervention_description")),
            status=_clean(r.get("completion_status")),
            due_date=_clean(r.get("due_date")),
            details=(
                f"Type: {_clean(r.get('intervention_type'))}\n"
                f"Status: {_clean(r.get('completion_status'))}\n"
                f"Due: {_clean(r.get('due_date'))}\n"
                f"Description: {_clean(r.get('intervention_description'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("intervention_id"), "HAS_INTERVENTION")
        add_edge(r.get("related_goal_id"), r.get("intervention_id"), "HAS_INTERVENTION")
        add_edge(r.get("intervention_id"), r.get("related_barrier_id"), "TARGETS_BARRIER")

    for r in rows("daily_notes"):
        add_node(
            r.get("note_id"),
            "DailyNote",
            date=_clean(r.get("note_date")),
            participation=_clean(r.get("participation_level")),
            text=_clean(r.get("note_text")),
            follow_up=_clean(r.get("follow_up_required_flag")),
            details=(
                f"Date: {_clean(r.get('note_date'))}\n"
                f"Participation: {_clean(r.get('participation_level'))}\n"
                f"Follow-up Required: {_clean(r.get('follow_up_required_flag'))}\n"
                f"Note: {_clean(r.get('note_text'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("note_id"), "HAS_DAILY_NOTE")

    for r in rows("support_plans"):
        add_node(
            r.get("support_plan_id"),
            "SupportPlan",
            plan_type=_clean(r.get("plan_type")),
            need=_clean(r.get("support_need")),
            strategy=_clean(r.get("support_strategy")),
            details=(
                f"Type: {_clean(r.get('plan_type'))}\n"
                f"Need: {_clean(r.get('support_need'))}\n"
                f"Strategy: {_clean(r.get('support_strategy'))}\n"
                f"Trigger: {_clean(r.get('trigger_condition'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("support_plan_id"), "HAS_SUPPORT_PLAN")

    for r in rows("incidents_and_risks"):
        add_node(
            r.get("incident_id"),
            "IncidentRisk",
            type=_clean(r.get("incident_type")),
            category=_clean(r.get("risk_category")),
            description=_clean(r.get("incident_description")),
            status=_clean(r.get("closure_status")),
            details=(
                f"Type: {_clean(r.get('incident_type'))}\n"
                f"Category: {_clean(r.get('risk_category'))}\n"
                f"Status: {_clean(r.get('closure_status'))}\n"
                f"Description: {_clean(r.get('incident_description'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("incident_id"), "HAS_INCIDENT_OR_RISK")

    for r in rows("appointments"):
        add_node(
            r.get("appointment_id"),
            "Appointment",
            type=_clean(r.get("appointment_type")),
            reason=_clean(r.get("reason_for_visit")),
            outcome=_clean(r.get("outcome_summary")),
            follow_up=_clean(r.get("follow_up_needed")),
            details=(
                f"Type: {_clean(r.get('appointment_type'))}\n"
                f"Date: {_clean(r.get('appointment_date'))}\n"
                f"Reason: {_clean(r.get('reason_for_visit'))}\n"
                f"Outcome: {_clean(r.get('outcome_summary'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("appointment_id"), "HAS_APPOINTMENT")

    for r in rows("medications"):
        add_node(
            r.get("medication_id"),
            "Medication",
            name=_clean(r.get("medication_name")),
            purpose=_clean(r.get("medication_purpose")),
            concern=_clean(r.get("adherence_concern_flag")),
            details=(
                f"Medication: {_clean(r.get('medication_name'))}\n"
                f"Purpose: {_clean(r.get('medication_purpose'))}\n"
                f"Adherence Concern: {_clean(r.get('adherence_concern_flag'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("medication_id"), "TAKES_MEDICATION")

    for r in rows("care_team_members"):
        add_node(
            r.get("care_team_member_id"),
            "CareTeamMember",
            name=_clean(r.get("name")),
            role=_clean(r.get("role")),
            organization=_clean(r.get("organization")),
            details=(
                f"Name: {_clean(r.get('name'))}\n"
                f"Role: {_clean(r.get('role'))}\n"
                f"Organization: {_clean(r.get('organization'))}"
            ),
        )
        add_edge(r.get("patient_id"), r.get("care_team_member_id"), "HAS_CARE_TEAM_MEMBER")

    return graph


@lru_cache(maxsize=1)
def get_graph() -> nx.MultiDiGraph:
    """Return the knowledge graph for the loaded dataset (built once)."""
    return build_graph(load_dataset())


def patient_graph_facts(
    graph: nx.MultiDiGraph, patient_id: str, max_items: int = 60
) -> List[str]:
    """Collect compact, human-readable graph facts around a patient.

    These facts form the structured context passed to the language model.
    """
    if patient_id == "all" or patient_id not in graph:
        return []

    facts: List[str] = []

    for _, dst, edge in graph.out_edges(patient_id, data=True):
        node = graph.nodes[dst]
        relation = edge.get("relation", "RELATED_TO")
        label = node.get("label", "Entity")
        description = (
            node.get("description")
            or node.get("text")
            or node.get("strategy")
            or node.get("outcome")
            or node.get("reason")
            or node.get("name")
            or node.get("details")
            or ""
        )
        status = node.get("status") or node.get("severity") or node.get("participation") or ""
        facts.append(f"{patient_id} -[{relation}]-> {dst} ({label}) | {description} | {status}")

    # Second hop: goals → barriers/interventions.
    for _, goal, _ in graph.out_edges(patient_id, data=True):
        if graph.nodes[goal].get("label") != "Goal":
            continue
        for _, dst, edge in graph.out_edges(goal, data=True):
            node = graph.nodes[dst]
            facts.append(
                f"{goal} -[{edge.get('relation')}]-> {dst} ({node.get('label')}) | "
                f"{node.get('description') or node.get('type') or ''} | "
                f"{node.get('status') or node.get('severity') or ''}"
            )

    return facts[:max_items]


def patient_subgraph_nodes(
    graph: nx.MultiDiGraph, patient_id: str, max_nodes: int = 120
) -> Set[str]:
    """Return the node set for a patient's full two-hop neighbourhood."""
    if patient_id == "all" or patient_id not in graph:
        nodes = list(graph.nodes())
        return set(nodes[:max_nodes])

    nodes: Set[str] = {patient_id}
    for _, dst in graph.out_edges(patient_id):
        nodes.add(dst)
    for node in list(nodes):
        for _, dst in graph.out_edges(node):
            nodes.add(dst)

    return set(list(nodes)[:max_nodes])
