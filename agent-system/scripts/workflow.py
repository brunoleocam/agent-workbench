"""The declared execution graph: loading, structural validation, condition matching, routing, and Mermaid.

Shared by validate_workflow.py and next_step.py so the validator and the router read the graph the same way. Stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path

SYSTEM_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

CLASSES = ("GREENFIELD", "FEATURE", "BUG_FIX", "REFACTORING", "INVESTIGATION", "CHANGE_DURING_IMPLEMENTATION")
COMPLEXITY = ("XS", "S", "M", "L", "XL")
SECURITY = ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
INTERFACES = ("new", "existing", "none")
RESULTS = ("pass", "fail", "escalate")
KINDS = {"agent": "agent", "script": "script", "human": "question"}
WHEN_KEYS = ("class", "complexity_min", "complexity_max", "security_min", "security_max", "interface", "design_approved")
GATE_SCRIPT = "validate_verification.py"
DEFAULT_MAX_REVISIONS = 3


class WorkflowError(Exception):
    """The graph file is missing or is not JSON (exit 2)."""


class ArgumentError(Exception):
    """A condition needs an argument the caller did not give (exit 2)."""


def default_path() -> Path:
    # Plugin: agent-system/workflow.json. Project copy: .cursor/agent-system/workflow.json. Both sit next to scripts/.
    return SYSTEM_DIR / "workflow.json"


def load(path: Path) -> dict:
    if not path.is_file():
        raise WorkflowError(f"workflow file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"workflow file is not valid JSON (line {exc.lineno}): {path}") from exc
    if not isinstance(data, dict):
        raise WorkflowError("workflow file must be a JSON object")
    return data


def nodes_by_id(graph: dict) -> dict[str, dict]:
    return {str(node.get("id")): node for node in graph.get("nodes") or [] if isinstance(node, dict)}


def max_revisions(graph: dict) -> int:
    value = (graph.get("limits") or {}).get("max_revisions", DEFAULT_MAX_REVISIONS)
    return value if isinstance(value, int) and not isinstance(value, bool) else DEFAULT_MAX_REVISIONS


# ---------------------------------------------------------------- validation


def _when_problems(when) -> list[str]:
    if not isinstance(when, dict):
        return ["`when` must be an object"]
    problems = []
    for key, value in when.items():
        if key not in WHEN_KEYS:
            problems.append(f"unknown `when` key '{key}'")
        elif key == "class":
            if not isinstance(value, list) or not value or any(item not in CLASSES for item in value):
                problems.append(f"`class` must be a non-empty list of {', '.join(CLASSES)}")
        elif key.startswith("complexity_"):
            if value not in COMPLEXITY:
                problems.append(f"`{key}` must be one of {', '.join(COMPLEXITY)}")
        elif key.startswith("security_"):
            if value not in SECURITY:
                problems.append(f"`{key}` must be one of {', '.join(SECURITY)}")
        elif key == "interface":
            if value not in INTERFACES:
                problems.append(f"`interface` must be one of {', '.join(INTERFACES)}")
        elif key == "design_approved" and not isinstance(value, bool):
            problems.append("`design_approved` must be true or false")
    return problems


def _agent_only_cycle(nodes: dict[str, dict], edges: list[dict]) -> list[str] | None:
    """A cycle whose nodes are all agents: nothing deterministic or human stops it."""
    agents = {node_id for node_id, node in nodes.items() if node.get("kind") == "agent"}
    succ: dict[str, list[str]] = {node_id: [] for node_id in agents}
    for edge in edges:
        if edge.get("from") in agents and edge.get("to") in agents:
            succ[edge["from"]].append(edge["to"])
    color = dict.fromkeys(agents, 0)
    stack: list[str] = []

    def visit(node_id: str) -> list[str] | None:
        color[node_id] = 1
        stack.append(node_id)
        for nxt in succ[node_id]:
            if color[nxt] == 1:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == 0:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node_id] = 2
        return None

    for node_id in sorted(agents):
        if color[node_id] == 0:
            found = visit(node_id)
            if found:
                return found
    return None


def validate(graph: dict, registry: dict | None, scripts_dir: Path = SCRIPTS_DIR, state_keys: set[str] | None = None) -> list[dict]:
    """Structural errors as {code, message, ref}. Empty list means the graph is valid.

    `registry` is agents.json; `state_keys` is init_project.default_state() keys, or None where init_project.py
    is not available (a project copy), which skips the state-ownership check.
    """
    errors: list[dict] = []

    def err(code: str, message: str, ref: str = "") -> None:
        errors.append({"code": code, "message": message, "ref": ref})

    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        err("structure", "`nodes` and `edges` must be lists")
        return errors

    nodes: dict[str, dict] = {}
    for node in raw_nodes:
        node_id = node.get("id") if isinstance(node, dict) and isinstance(node.get("id"), str) else ""
        if not node_id:
            err("node-missing-field", "a node has no `id`")
            continue
        if node_id in nodes:
            err("duplicate-node", f"node id '{node_id}' is declared more than once", node_id)
            continue
        nodes[node_id] = node
        kind = node.get("kind")
        if kind not in KINDS:
            err("unknown-kind", f"node '{node_id}' has kind '{kind}' (agent, script, or human)", node_id)
            continue
        field = KINDS[kind]
        if not node.get(field) or not node.get("description"):
            err("node-missing-field", f"{kind} node '{node_id}' needs `{field}` and `description`", node_id)

    start = graph.get("start")
    if start not in nodes:
        err("unknown-start", f"start node '{start}' does not exist", str(start))

    limit = (graph.get("limits") or {}).get("max_revisions", DEFAULT_MAX_REVISIONS)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 10:
        err("bad-limit", "`limits.max_revisions` must be an integer from 1 to 10", "max_revisions")

    edges: list[dict] = []
    groups: dict[tuple[str, str], set] = {}
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, dict):
            err("structure", f"edge #{index} is not an object")
            continue
        ref = f"{edge.get('from')}->{edge.get('to')}"
        if any(not isinstance(edge.get(key), str) for key in ("from", "to")) or any(
            key in edge and not isinstance(edge[key], str) for key in ("group", "join", "on")
        ):
            err("structure", f"edge #{index} ({ref}): `from`, `to`, `group`, `join`, and `on` must be strings", f"edge #{index}")
            continue
        missing = [end for end in (edge.get("from"), edge.get("to")) if end not in nodes]
        if missing:
            err("unknown-edge-node", f"edge {ref} points to unknown node(s): {', '.join(str(item) for item in missing)}", ref)
            continue
        edges.append(edge)
        if "on" in edge and edge["on"] not in RESULTS:
            err("bad-on", f"edge {ref} has `on: {edge['on']}` (pass, fail, or escalate)", ref)
        if "when" in edge:
            for problem in _when_problems(edge["when"]):
                err("bad-when", f"edge {ref}: {problem}", ref)
        if "group" in edge or "join" in edge:
            if not edge.get("group") or not edge.get("join"):
                err("group-without-join", f"edge {ref} has a `group` without a `join` (or a `join` without a `group`)", ref)
            elif edge["join"] not in nodes:
                err("unknown-edge-node", f"edge {ref} joins at unknown node '{edge['join']}'", ref)
            else:
                groups.setdefault((edge["from"], edge["group"]), set()).add(edge["join"])

    for (source, group), joins in sorted(groups.items()):
        if len(joins) > 1:
            err("group-join-mismatch", f"group '{group}' from '{source}' has more than one join: {', '.join(sorted(joins))}", group)
            continue
        join = next(iter(joins))
        for edge in edges:
            if edge["from"] == source and edge.get("group") == group:
                branch = edge["to"]
                if not any(item["from"] == branch and item["to"] == join for item in edges):
                    err("group-branch-no-join", f"branch '{branch}' of group '{group}' has no edge to its join '{join}'", branch)

    if start in nodes:
        seen = {start}
        frontier = [start]
        while frontier:
            current = frontier.pop()
            for edge in edges:
                if edge["from"] == current and edge["to"] not in seen:
                    seen.add(edge["to"])
                    frontier.append(edge["to"])
        for node_id in nodes:
            if node_id not in seen:
                err("unreachable", f"node '{node_id}' cannot be reached from '{start}'", node_id)

    cycle = _agent_only_cycle(nodes, edges)
    if cycle:
        err("agent-only-cycle", f"cycle of agent nodes with no script or human node: {' -> '.join(cycle)}", cycle[0])

    for node_id, node in nodes.items():
        if node.get("kind") == "script" and node.get("script") and not (scripts_dir / str(node["script"])).is_file():
            err("missing-script", f"script node '{node_id}' runs '{node['script']}', which is not in {scripts_dir.name}/", node_id)
        if node.get("kind") == "script" and node.get("script") == GATE_SCRIPT:
            outs = {edge.get("on") for edge in edges if edge["from"] == node_id}
            if "fail" not in outs:
                err("gate-without-fail", f"gate '{node_id}' has no `on: fail` edge", node_id)
            if "escalate" not in outs:
                err("gate-without-escalate", f"gate '{node_id}' has no `on: escalate` edge for the revision limit", node_id)

    if registry is not None:
        agents = [item for item in registry.get("agents") or [] if isinstance(item, dict)]
        known = {str(item.get("name")) for item in agents}
        used = {str(node.get("agent")) for node in nodes.values() if node.get("kind") == "agent"}
        for node_id, node in nodes.items():
            if node.get("kind") == "agent" and node.get("agent") and node["agent"] not in known:
                err("unknown-agent", f"node '{node_id}' uses agent '{node['agent']}', which is not in agents.json", node_id)
        for item in agents:
            name = str(item.get("name"))
            if item.get("scope") == "user" and name != "orchestrator" and name not in used:
                err("agent-without-node", f"agent '{name}' from agents.json has no node in the graph", name)

    if state_keys is not None:
        fields = graph.get("state_fields")
        if not isinstance(fields, dict):
            err("state-fields", "`state_fields` must be an object")
        else:
            for key in sorted(state_keys - set(fields)):
                err("state-field-missing", f"state key '{key}' from default_state() has no owner in `state_fields`", key)
            for key in sorted(set(fields) - state_keys):
                err("state-field-unknown", f"`state_fields` declares '{key}', which default_state() does not have", key)
            for key, writers in sorted(fields.items()):
                if not isinstance(writers, list) or not writers:
                    err("state-writer-unknown", f"state key '{key}' needs a non-empty list of writers", key)
                    continue
                for writer in writers:
                    if writer != "hook" and not (scripts_dir / str(writer)).is_file():
                        err("state-writer-unknown", f"state key '{key}' lists writer '{writer}', which is neither `hook` nor a script", key)
    return errors


# ---------------------------------------------------------------- routing


def _rank(order: tuple[str, ...], value: str) -> int:
    return order.index(value)


def match(when: dict | None, ctx: dict) -> tuple[bool, list[str]]:
    """Whether every key of `when` holds for ctx, with the reasons. Raises ArgumentError for a missing input."""
    reasons: list[str] = []
    for key, expected in (when or {}).items():
        if key == "class":
            value = ctx.get("class")
            if value is None:
                raise ArgumentError("this step depends on --class")
            if value not in expected:
                return False, []
            reasons.append(f"class {value}")
        elif key.startswith("complexity_") or key.startswith("security_"):
            name = "complexity" if key.startswith("complexity_") else "security"
            order = COMPLEXITY if name == "complexity" else SECURITY
            value = ctx.get(name)
            if value is None:
                raise ArgumentError(f"this step depends on --{name}")
            low = key.endswith("_min")
            ok = _rank(order, value) >= _rank(order, expected) if low else _rank(order, value) <= _rank(order, expected)
            if not ok:
                return False, []
            reasons.append(f"{name} {value} {'>=' if low else '<='} {expected}")
        elif key == "interface":
            value = ctx.get("interface")
            if value is None:
                raise ArgumentError("this step depends on --interface (new, existing, or none)")
            if value != expected:
                return False, []
            reasons.append(f"interface {expected}")
        elif key == "design_approved":
            if bool(ctx.get("design_approved")) != expected:
                return False, []
            reasons.append("design approved" if expected else "design not approved")
    return True, reasons


def route(graph: dict, source: str, ctx: dict, result: str = "pass", revisions: int | None = None) -> dict:
    """The next node(s) from `source`. Raises ArgumentError for bad input."""
    nodes = nodes_by_id(graph)
    if source not in nodes:
        raise ArgumentError(f"unknown node '{source}'")
    if result not in RESULTS:
        raise ArgumentError(f"--result must be one of {', '.join(RESULTS)}")
    reasons: list[str] = []
    node = nodes[source]
    if node.get("kind") == "script" and node.get("script") == GATE_SCRIPT and result == "fail":
        if revisions is None:
            raise ArgumentError("a failed gate needs --feature to read its revision count")
        limit = max_revisions(graph)
        if revisions >= limit:
            result = "escalate"
            reasons.append(f"revisions {revisions} >= max_revisions {limit}")
        else:
            reasons.append(f"revisions {revisions} < max_revisions {limit}")
    outgoing = [edge for edge in graph.get("edges") or [] if edge.get("from") == source]
    answer = {"from": source, "result": result, "next": [], "nodes": [], "parallel": False, "join": None, "reason": reasons, "status": "continue"}
    if not outgoing:
        answer["status"] = "done"
        answer["reason"] = reasons + [f"'{source}' is a terminal node"]
        return answer
    chosen: list[tuple[dict, list[str]]] = []
    group = None
    for edge in outgoing:
        if "on" in edge and edge["on"] != result:
            continue
        if group is not None and edge.get("group") != group:
            continue
        ok, why = match(edge.get("when"), ctx)
        if not ok:
            continue
        chosen.append((edge, why))
        if not edge.get("group"):
            break
        group = edge["group"]
    if not chosen:
        answer["status"] = "no_match"
        answer["reason"] = reasons + [f"no edge from '{source}' holds for result '{result}' and the given context"]
        return answer
    for edge, why in chosen:
        target = nodes[edge["to"]]
        answer["next"].append(edge["to"])
        item = {"id": edge["to"], "kind": target.get("kind"), "description": target.get("description")}
        field = KINDS.get(str(target.get("kind")))
        if field:
            item[field] = target.get(field)
        answer["nodes"].append(item)
        label = f"on {edge['on']}" if "on" in edge else "any result"
        answer["reason"].append(f"{source} -> {edge['to']}: {', '.join([label, *why])}")
    if group:
        answer["parallel"] = len(chosen) > 1
        answer["join"] = chosen[0][0].get("join")
    humans = [item for item in answer["nodes"] if item["kind"] == "human"]
    if humans:
        answer["status"] = "needs_decision"
        answer["question"] = humans[0]["question"]
    return answer


# ---------------------------------------------------------------- mermaid


def _edge_label(edge: dict) -> str:
    parts = []
    if edge.get("on"):
        parts.append(edge["on"])
    for key, value in (edge.get("when") or {}).items():
        if key == "class":
            parts.append("/".join(value))
        elif key == "complexity_min":
            parts.append(f"{value}+")
        elif key == "complexity_max":
            parts.append(f"up to {value}")
        elif key == "security_min":
            parts.append(f"security {value}+")
        elif key == "security_max":
            parts.append(f"security up to {value}")
        elif key == "interface":
            parts.append(f"{value} UI")
        elif key == "design_approved":
            parts.append("design approved" if value else "no DESIGN.md")
    if edge.get("group"):
        parts.append(f"parallel {edge['group']}")
    return ", ".join(parts)


def mermaid(graph: dict) -> str:
    lines = ["flowchart TD"]
    for node in graph.get("nodes") or []:
        kind = node.get("kind")
        detail = node.get("agent") if kind == "agent" else node.get("script") if kind == "script" else "human decision"
        label = f"{node['id']}<br/>{detail}".replace('"', "'")
        if kind == "script":
            lines.append(f'    {node["id"]}[["{label}"]]')
        elif kind == "human":
            lines.append(f'    {node["id"]}{{{{"{label}"}}}}')
        else:
            lines.append(f'    {node["id"]}["{label}"]')
    for edge in graph.get("edges") or []:
        arrow = "-.->" if edge.get("on") in {"fail", "escalate"} else "-->"
        label = _edge_label(edge)
        lines.append(f"    {edge['from']} {arrow}|{label}| {edge['to']}" if label else f"    {edge['from']} {arrow} {edge['to']}")
    return "\n".join(lines) + "\n"
