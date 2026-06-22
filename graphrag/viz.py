"""Serialize knowledge-graph subgraphs into vis-network JSON for the frontend.

Node styling is defined once here and exposed to the UI (legend + rendering) so
the backend remains the single source of truth for the visual language.
"""

from __future__ import annotations

import networkx as nx

# Visual style per node type: colour, shape, and relative size.
NODE_STYLE: dict[str, dict[str, object]] = {
    "Patient": {"color": "#2B6CB0", "shape": "dot", "size": 28},
    "Goal": {"color": "#38A169", "shape": "box", "size": 22},
    "Barrier": {"color": "#E53E3E", "shape": "diamond", "size": 22},
    "Intervention": {"color": "#DD6B20", "shape": "triangle", "size": 20},
    "DailyNote": {"color": "#718096", "shape": "ellipse", "size": 16},
    "SupportPlan": {"color": "#805AD5", "shape": "box", "size": 20},
    "IncidentRisk": {"color": "#9B2C2C", "shape": "star", "size": 22},
    "Appointment": {"color": "#D69E2E", "shape": "ellipse", "size": 18},
    "Medication": {"color": "#319795", "shape": "ellipse", "size": 18},
    "CareTeamMember": {"color": "#4A5568", "shape": "dot", "size": 16},
    "Program": {"color": "#3182CE", "shape": "box", "size": 18},
}

_DEFAULT_STYLE = {"color": "#A0AEC0", "shape": "dot", "size": 15}

# Human-readable legend labels in display order.
LEGEND = [
    {"type": label, "label": label, **NODE_STYLE[label]}
    for label in (
        "Patient",
        "Goal",
        "Barrier",
        "Intervention",
        "DailyNote",
        "SupportPlan",
        "IncidentRisk",
        "Appointment",
        "Medication",
        "Program",
    )
]


def _short_label(node_id: str, attrs: dict) -> str:
    """Build a concise two-line node caption."""
    label = attrs.get("label", "Entity")
    captions = {
        "Patient": ("Patient", attrs.get("name")),
        "Goal": ("Goal", attrs.get("category")),
        "Barrier": ("Barrier", attrs.get("type")),
        "Intervention": ("Intervention", attrs.get("type")),
        "DailyNote": ("Daily Note", attrs.get("date")),
        "SupportPlan": (attrs.get("plan_type") or "Support Plan", attrs.get("need")),
        "IncidentRisk": ("Incident", attrs.get("type")),
        "Appointment": ("Appointment", attrs.get("type")),
        "Medication": ("Medication", attrs.get("name")),
        "CareTeamMember": ("Care Team", attrs.get("role")),
        "Program": ("Program", attrs.get("type")),
    }
    title, subtitle = captions.get(label, (label, node_id))
    return f"{title}\n{subtitle or node_id}"


def serialize_subgraph(graph: nx.MultiDiGraph, nodes: set[str]) -> dict[str, list[dict]]:
    """Return ``{"nodes": [...], "edges": [...]}`` for the given node set."""
    if not nodes:
        return {"nodes": [], "edges": []}

    sub = graph.subgraph(nodes)

    out_nodes = []
    for node_id, attrs in sub.nodes(data=True):
        node_type = attrs.get("label", "Entity")
        style = NODE_STYLE.get(node_type, _DEFAULT_STYLE)
        tooltip = (
            attrs.get("details")
            or attrs.get("description")
            or attrs.get("text")
            or node_id
        )
        out_nodes.append(
            {
                "id": node_id,
                "label": _short_label(node_id, attrs),
                "title": str(tooltip),
                "type": node_type,
                "color": style["color"],
                "shape": style["shape"],
                "size": style["size"],
            }
        )

    seen = set()
    out_edges = []
    for src, dst, attrs in sub.edges(data=True):
        relation = attrs.get("relation", "RELATED_TO")
        key = (src, dst, relation)
        if key in seen:
            continue
        seen.add(key)
        out_edges.append({"from": src, "to": dst, "label": relation})

    return {"nodes": out_nodes, "edges": out_edges}
