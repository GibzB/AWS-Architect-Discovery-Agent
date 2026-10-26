"""Diagram Generator — produces Mermaid diagrams from architecture."""

from typing import Any


def generate_mermaid_diagram(session: dict[str, Any]) -> str:
    """Generate a Mermaid architecture diagram from session data.

    If the Architect Agent already produced a diagram, return that.
    Otherwise, generate a basic one from the services list.
    """
    arch = session.get("architecture", {})

    # Use architect-generated diagram if available
    existing = arch.get("diagram_mermaid", "")
    if existing:
        return existing

    # Generate from services list
    services = arch.get("services", [])
    if not services:
        return "graph TD\n  A[No architecture designed yet]"

    lines = ["graph TD"]
    lines.append("  Client[Client/Browser]")

    # Group services by layer
    networking = []
    compute = []
    storage = []
    other = []

    for svc in services:
        name = svc.get("service", "")
        if any(kw in name.lower() for kw in ["cloudfront", "api gateway", "route 53", "elb", "alb"]):
            networking.append(svc)
        elif any(kw in name.lower() for kw in ["ecs", "lambda", "ec2", "fargate", "eks"]):
            compute.append(svc)
        elif any(kw in name.lower() for kw in ["s3", "rds", "dynamodb", "elasticache", "aurora"]):
            storage.append(svc)
        else:
            other.append(svc)

    # Build connections
    node_id = 0

    def make_id():
        nonlocal node_id
        node_id += 1
        return f"N{node_id}"

    prev_ids = ["Client"]

    # Networking layer
    if networking:
        net_ids = []
        for svc in networking:
            nid = make_id()
            clean_name = svc["service"].replace("Amazon ", "").replace("AWS ", "")
            lines.append(f"  {nid}[{clean_name}]")
            for pid in prev_ids:
                lines.append(f"  {pid} --> {nid}")
            net_ids.append(nid)
        prev_ids = net_ids

    # Compute layer
    if compute:
        comp_ids = []
        for svc in compute:
            nid = make_id()
            clean_name = svc["service"].replace("Amazon ", "").replace("AWS ", "")
            lines.append(f"  {nid}[{clean_name}]")
            for pid in prev_ids:
                lines.append(f"  {pid} --> {nid}")
            comp_ids.append(nid)
        prev_ids = comp_ids

    # Storage layer
    if storage:
        for svc in storage:
            nid = make_id()
            clean_name = svc["service"].replace("Amazon ", "").replace("AWS ", "")
            lines.append(f"  {nid}[({clean_name})]")
            for pid in prev_ids:
                lines.append(f"  {pid} --> {nid}")

    # Other services connect to compute
    if other and compute:
        for svc in other:
            nid = make_id()
            clean_name = svc["service"].replace("Amazon ", "").replace("AWS ", "")
            lines.append(f"  {nid}{{{{{clean_name}}}}}")
            for pid in prev_ids[:1]:  # Connect to first compute node
                lines.append(f"  {pid} -.-> {nid}")

    return "\n".join(lines)
