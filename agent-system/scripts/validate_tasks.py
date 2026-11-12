"""Structural validation of a task plan: links to REQ/AC, verification, dependencies, status, and evidence.

Granularity and plan quality stay with the planner. This script checks structure only.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import (  # noqa: E402
    Block,
    Bundle,
    ConfigError,
    Report,
    add_common_args,
    config_error,
    load_bundle,
    load_proofs,
    record,
    task_status,
    truthy,
)


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    cycles, seen_keys = [], set()
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt) :] + [nxt]
                key = frozenset(cycle)
                if key not in seen_keys:
                    seen_keys.add(key)
                    cycles.append(cycle)
            elif state.get(nxt) is None:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node) is None:
            visit(node)
    return cycles


def tests_for(task: Block, tests: list[Block]) -> list[str]:
    linked = task.ids("verification", "TEST")
    for test in tests:
        if task.id in test.ids("task", "TASK") and test.id not in linked:
            linked.append(test.id)
    return linked


def validate(bundle: Bundle, report: Report) -> None:
    tasks = bundle.task_blocks()
    tests = bundle.test_blocks()
    spec_reqs = {b.id for b in bundle.spec.of_kind("REQ")} if bundle.spec else None
    spec_acs = {b.id: b for b in bundle.spec.of_kind("AC")} if bundle.spec else None
    if bundle.spec is None:
        report.warn("no-spec", "No spec found for this feature; REQ and AC links are not cross-checked.")
    if not tasks:
        report.fail("no-tasks", "No task found (heading starting with TASK-NNN).")
        return
    report.ok("tasks-found", f"{len(tasks)} tasks and {len(tests)} test definitions found.")

    for item, total in Counter(block.id for block in tasks + tests).items():
        if total > 1:
            report.fail("duplicate-id", f"{item} is defined more than once.", item)

    task_ids = {task.id for task in tasks}
    test_ids = {test.id: test for test in tests}
    proofs = load_proofs(bundle.root, bundle.slug)["by_test"]
    statuses: dict[str, str | None] = {}
    graph: dict[str, list[str]] = {}
    covered_acs: set[str] = set()

    for task in tasks:
        status = task_status(task.get("status"))
        statuses[task.id] = status
        if not task.title:
            report.fail("task-no-description", f"{task.id} has no description in its heading.", task.id)
        reqs, acs = task.ids("requirements", "REQ"), task.ids("acceptance", "AC")
        covered_acs.update(acs)
        if not reqs and not acs:
            report.fail("task-unlinked", f"{task.id} references no requirement or acceptance criterion.", task.id)
        elif not acs:
            report.warn("task-no-ac", f"{task.id} references no acceptance criterion.", task.id)
        if spec_reqs is not None:
            for item in reqs:
                if item not in spec_reqs:
                    report.fail("task-unknown-req", f"{task.id} references unknown requirement {item}.", task.id)
            for item in acs:
                if item not in spec_acs:
                    report.fail("task-unknown-ac", f"{task.id} references unknown acceptance criterion {item}.", task.id)
        linked_tests = tests_for(task, tests)
        for item in task.ids("verification", "TEST"):
            if item not in test_ids:
                report.fail("task-unknown-test", f"{task.id} names {item}, which has no TEST definition.", task.id)
        if not linked_tests and not task.get("verification"):
            report.fail("task-no-verification", f"{task.id} has no verification.", task.id)
        if not task.get("done_when"):
            report.fail("task-no-done-when", f"{task.id} has no completion criterion (Done when).", task.id)
        if not task.get("gate"):
            report.warn("task-no-gate", f"{task.id} has no validation gate.", task.id)
        if status is None:
            report.fail("task-status", f"{task.id} has missing or unknown status '{task.get('status')}'.", task.id)
        depends = task.ids("depends", "TASK")
        graph[task.id] = depends
        for item in depends:
            if item not in task_ids:
                report.fail("task-unknown-dependency", f"{task.id} depends on unknown task {item}.", task.id)
        if status == "blocked" and not depends and not task.get("blocked_by"):
            report.fail("task-blocked-no-cause", f"{task.id} is blocked without a dependency or 'Blocked by'.", task.id)
        if status == "done":
            required = [item for item in linked_tests if item in test_ids and truthy(test_ids[item].get("required"), True)]
            if required:
                missing = [item for item in required if (proofs.get(item) or {}).get("status") != "PASS"]
                if missing:
                    report.fail("task-done-no-proof", f"{task.id} is done without a passing proof for {', '.join(missing)}.", task.id)
            elif not task.get("evidence"):
                report.fail("task-done-no-evidence", f"{task.id} is done without evidence (TEST proof or 'Evidence').", task.id)

    for task in tasks:
        if statuses.get(task.id) == "done":
            pending = [item for item in graph.get(task.id, []) if statuses.get(item) not in {"done", "cancelled", None}]
            if pending:
                report.warn("done-before-dependency", f"{task.id} is done while {', '.join(pending)} is not.", task.id)
    for cycle in find_cycles(graph):
        report.fail("dependency-cycle", "Circular dependency: " + " -> ".join(cycle) + ".", cycle[0])

    for test in tests:
        if not test.get("command"):
            level = report.fail if truthy(test.get("required"), True) else report.warn
            level("test-no-command", f"{test.id} has no Command.", test.id)
        acs = test.ids("acceptance", "AC")
        if not acs:
            report.fail("test-no-ac", f"{test.id} covers no acceptance criterion.", test.id)
        if spec_acs is not None:
            for item in acs:
                if item not in spec_acs:
                    report.fail("test-unknown-ac", f"{test.id} references unknown acceptance criterion {item}.", test.id)
        for item in test.ids("task", "TASK"):
            if item not in task_ids:
                report.fail("test-unknown-task", f"{test.id} references unknown task {item}.", test.id)

    if spec_acs is not None:
        tested = {item for test in tests for item in test.ids("acceptance", "AC")}
        for item in spec_acs:
            if item not in covered_acs:
                report.warn("ac-no-task", f"{item} is not covered by any task.", item)
            if item not in tested:
                report.warn("ac-no-test", f"{item} has no TEST definition.", item)
    report.data["counts"] = {
        "tasks": len(tasks),
        "tests": len(tests),
        "by_status": dict(Counter(status or "unknown" for status in statuses.values())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the structure and traceability of a task plan.")
    add_common_args(parser)
    parser.add_argument("--tasks", help="tasks path relative to the root (overrides --feature)")
    parser.add_argument("--spec", help="spec path for REQ/AC cross-check")
    parser.add_argument("--tests", help="extra file with TEST definitions")
    args = parser.parse_args()
    try:
        bundle = load_bundle(args, need=("tasks",))
        report = Report("Task validation", strict=args.strict)
        report.data.update({"tasks": bundle.rel(bundle.tasks), "spec": bundle.rel(bundle.spec)})
        validate(bundle, report)
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    code = report.emit(args.json)
    result = "passed" if code == 0 else f"failed fail={report.count('FAIL')} warn={report.count('WARN')}"
    record(bundle.root, "TASK_VALIDATION_COMPLETED", f"validate_tasks {bundle.slug}", result, bundle.slug, "orchestrator", not args.no_record,
           node="tasks_check", inputs=[bundle.rel(bundle.tasks), bundle.rel(bundle.spec), *(bundle.rel(doc) for doc in bundle.tests)])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
