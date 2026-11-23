"""Closing gate for a feature: every criterion tested, every required test proven on the current code,
independent review done, blocking findings resolved, accepted risks justified, and task states consistent."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_spec  # noqa: E402
import validate_tasks  # noqa: E402
from artifacts import (  # noqa: E402
    Bundle,
    ConfigError,
    Document,
    Report,
    add_common_args,
    artifact_path,
    config_error,
    load_bundle,
    load_document,
    load_proofs,
    mutation_pending,
    mutation_threshold,
    proofs_file,
    record,
    task_status,
    truthy,
    workspace_fingerprint,
)
from lib import redact, system_dir  # noqa: E402

REVIEW_STATUS = {"PASS", "PASS_WITH_WARNINGS", "FAIL"}
BLOCKING = {"blocker", "critical", "high"}
SERIOUS = {"major", "medium"}
FINDING_STATUS = {"open", "resolved", "accepted"}


def check_findings(doc: Document, label: str, kind: str, report: Report) -> None:
    for block in doc.of_kind(kind):
        severity = block.get("severity").lower()
        status = (block.get("status") or "open").lower()
        if status not in FINDING_STATUS:
            report.fail("finding-status", f"{label} {block.id} has unknown status '{status}' (open, resolved, accepted).", block.id)
            continue
        if status == "accepted" and not block.get("justification"):
            report.fail("accepted-without-justification", f"{label} {block.id} is accepted as residual risk without a Justification.", block.id)
        elif status == "open" and severity in BLOCKING:
            report.fail("blocking-finding", f"{label} {block.id} ({severity}) is still open: {block.title}.", block.id)
        elif status == "open" and severity in SERIOUS:
            report.warn("open-finding", f"{label} {block.id} ({severity}) is still open: {block.title}.", block.id)
        elif not severity:
            report.warn("finding-severity", f"{label} {block.id} has no Severity.", block.id)
        if kind == "SEC" and block.get("classification").lower() == "confirmed" and not block.get("location"):
            report.warn("finding-location", f"{label} {block.id} is confirmed but has no Location.", block.id)


def check_report_doc(doc: Document | None, label: str, kind: str, required: bool, current: str, report: Report) -> None:
    if doc is None:
        if required:
            report.fail(f"{label.lower()}-missing", f"{label} is required and was not found.")
        else:
            report.info(f"{label.lower()}-skipped", f"No {label.lower()} file (not required at this complexity and risk).")
        return
    status = doc.frontmatter.get("status", "").upper()
    if status not in REVIEW_STATUS:
        report.fail(f"{label.lower()}-status", f"{label} has missing or unknown status '{status}'.")
    elif status == "FAIL":
        report.fail(f"{label.lower()}-failed", f"{label} status is FAIL.")
    else:
        report.ok(f"{label.lower()}-status", f"{label} status is {status}.")
    recorded = doc.frontmatter.get("fingerprint", "").strip()
    code = label.lower().replace(" ", "-")
    if not recorded:
        if required:
            report.fail(f"{code}-fingerprint-missing", f"{label} has no fingerprint; record the digest from check_proofs.py --fingerprint.")
    elif recorded != current:
        message = f"{label} was recorded for another workspace state (fingerprint {recorded[:12]}, current {current[:12]})."
        if required:
            report.fail(f"{code}-stale", message)
        else:
            report.warn(f"{code}-stale", message)
    else:
        report.ok(f"{code}-fingerprint", f"{label} fingerprint matches the current workspace.")
    check_findings(doc, label, kind, report)


def mutation_targets(test, tasks: dict) -> list[str]:
    raw = test.get("mutate")
    if not raw:
        raw = next((tasks[task_id].get("mutate") for task_id in test.ids("task", "TASK") if tasks.get(task_id) and tasks[task_id].get("mutate")), "")
    return sorted({item.strip().strip("`").replace("\\", "/") for item in raw.split(",") if item.strip()}) if raw else []


def check_mutation_scores(bundle: Bundle, tests: list, digest: str, report: Report) -> None:
    if mutation_pending(bundle.root):
        report.fail("mutation-pending", "A check_mutation.py run is in progress or was interrupted, so a source file may still be mutated. Let it finish, or run check_mutation.py again to restore it.")
    threshold, source, problem = mutation_threshold(bundle.spec.frontmatter, bundle.layout)
    if problem:
        report.fail("mutation-min-invalid", problem)
        return
    if threshold is None:
        return
    tasks = {task.id: task for task in bundle.task_blocks()}
    declared = {test.id: (test, mutation_targets(test, tasks)) for test in tests if truthy(test.get("required"), True) and mutation_targets(test, tasks)}
    if not declared:
        message = f"mutation_min_score {threshold} is set ({source}) but no required TEST declares Mutate."
        (report.fail if source == "spec" else report.warn)("mutation-undeclared", message)
        return
    path = system_dir(bundle.root) / "proofs" / f"{bundle.slug}.mutation.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    except (OSError, json.JSONDecodeError):
        data = None
    recorded = data.get("tests") if isinstance(data, dict) and isinstance(data.get("tests"), dict) else None
    targets = data.get("targets") if isinstance(data, dict) and isinstance(data.get("targets"), dict) else {}
    if recorded is None:
        report.fail("mutation-missing", f"No mutation score for {bundle.slug}. Run check_mutation.py --feature {bundle.slug}.")
    elif data.get("status") != "MEASURED":
        report.fail("mutation-not-measured", f"Mutation run is {data.get('status')}: {data.get('reason') or ''}".rstrip(": "))
    elif data.get("fingerprint") != digest:
        report.fail("mutation-stale", "Mutation score predates the current workspace; rerun check_mutation.py.")
    elif set(recorded) != set(declared) or any(recorded.get(test_id) != redact(test.get("command"), 300) for test_id, (test, _) in declared.items()):
        report.fail("mutation-command-changed", "The TESTs that declare Mutate, or their commands, changed after the mutation score was recorded.")
    elif any(sorted(targets.get(test_id) or []) != files for test_id, (_, files) in declared.items()):
        report.fail("mutation-targets-changed", "The Mutate files changed after the mutation score was recorded; rerun check_mutation.py.")
    elif data.get("truncated"):
        report.fail("mutation-partial", "The mutation score comes from a partial run (time budget or --max-mutants); run check_mutation.py to completion.")
    elif float(data.get("score") or 0) < threshold:
        survivors = "; ".join(f"{name} {item}" for name, entry in (data.get("files") or {}).items() for item in (entry.get("survived") or [])[:2])
        report.fail("mutation-score", f"Mutation score {data.get('score')} is below {threshold} ({data.get('killed')}/{data.get('mutants')} killed; survived: {survivors}).")
    else:
        timeouts = sum(int((entry or {}).get("timeouts") or 0) for entry in (data.get("files") or {}).values())
        note = f", {timeouts} by timeout" if timeouts else ""
        report.ok("mutation", f"Mutation score {data.get('score')} meets {threshold} ({data.get('killed')}/{data.get('mutants')} killed{note}).")


def validate(bundle: Bundle, review: Document | None, security: Document | None, report: Report) -> None:
    spec = bundle.spec
    meta = spec.frontmatter
    complexity = meta.get("complexity", "").upper()
    risk = meta.get("security_risk", "").upper()

    for name, module, run in (
        ("spec", validate_spec, lambda sub: validate_spec.validate(spec, bundle.root, bundle.layout, sub, False)),
        ("tasks", validate_tasks, lambda sub: validate_tasks.validate(bundle, sub)),
    ):
        sub = Report(name)
        run(sub)
        for item in sub.items:
            if item["level"] == "FAIL":
                report.fail(f"{name}-{item['code']}", f"{name}: {item['message']}", item["ref"])
        if not sub.count("FAIL"):
            report.ok(f"{name}-structure", f"{name.capitalize()} structure is valid ({sub.count('WARN')} warnings; run validate_{name}.py for detail).")

    current = workspace_fingerprint(bundle.root, bundle.layout)
    report.data["fingerprint"] = current
    proofs = load_proofs(bundle.root, bundle.slug)["by_test"]
    tests = bundle.test_blocks()
    by_ac: dict[str, list] = {}
    for test in tests:
        for item in test.ids("acceptance", "AC"):
            by_ac.setdefault(item, []).append(test)

    for ac in spec.of_kind("AC"):
        if not truthy(ac.get("required"), True):
            continue
        linked = by_ac.get(ac.id, [])
        if not linked:
            report.fail("ac-no-check", f"{ac.id} has no TEST check.", ac.id)
        elif not any(truthy(test.get("required"), True) for test in linked):
            report.warn("ac-optional-only", f"{ac.id} is covered only by optional tests.", ac.id)

    proven = 0
    for test in tests:
        if not truthy(test.get("required"), True):
            continue
        proof = proofs.get(test.id)
        if not proof:
            report.fail("proof-missing", f"{test.id} has no proof. Run check_proofs.py.", test.id)
            continue
        status = proof.get("status")
        if status != "PASS":
            kind = "application or test failure" if status == "FAIL" else "environment or policy problem, not an application failure"
            report.fail("proof-not-pass", f"{test.id} proof is {status} ({kind}): {proof.get('reason') or ''}".rstrip(": "), test.id)
            continue
        if proof.get("fingerprint") != current["digest"]:
            report.fail("proof-stale", f"{test.id} proof predates the current workspace; rerun check_proofs.py.", test.id)
            continue
        if proof.get("command") != redact(test.get("command"), 300):
            report.fail("proof-command-changed", f"{test.id} command changed after its proof was recorded.", test.id)
            continue
        proven += 1
    if proven:
        report.ok("proofs", f"{proven} required checks proven on the current workspace.")
    check_mutation_scores(bundle, tests, current["digest"], report)

    for task in bundle.task_blocks():
        status = task_status(task.get("status"))
        if status not in {"done", "cancelled"}:
            report.fail("task-open", f"{task.id} is {status or 'without status'}; every task must be done or cancelled.", task.id)

    review_required = complexity not in {"XS", "S"}
    check_report_doc(review, "Review", "FIND", review_required, current["digest"], report)
    security_required = risk in {"HIGH", "CRITICAL"}
    check_report_doc(security, "Security review", "SEC", security_required, current["digest"], report)
    report.data["policy"] = {"complexity": complexity or None, "security_risk": risk or None, "review_required": review_required, "security_review_required": security_required}


def main() -> int:
    parser = argparse.ArgumentParser(description="Closing gate: criteria, proofs, review, findings, and task states.")
    add_common_args(parser)
    parser.add_argument("--spec", help="spec path relative to the root")
    parser.add_argument("--tasks", help="tasks path relative to the root")
    parser.add_argument("--tests", help="extra file with TEST definitions")
    parser.add_argument("--review", help="review report path (default: <reviews_dir>/<feature>.md)")
    parser.add_argument("--security", help="security assessment path (default: <security_dir>/<feature>.md)")
    args = parser.parse_args()
    try:
        bundle = load_bundle(args, need=("spec", "tasks"))
        docs = {}
        for name, key in (("review", "reviews_dir"), ("security", "security_dir")):
            explicit = getattr(args, name)
            path = artifact_path(bundle.root, explicit, bundle.layout, key, None if explicit else bundle.slug)
            if explicit and not path.is_file():
                raise ConfigError(f"{name} file not found: {explicit}")
            docs[name] = load_document(path) if path is not None and path.is_file() else None
        report = Report("Verification gate", strict=args.strict)
        report.data.update({"feature": bundle.slug, "review": bundle.rel(docs["review"]), "security": bundle.rel(docs["security"])})
        validate(bundle, docs["review"], docs["security"], report)
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    code = report.emit(args.json)
    result = "passed" if code == 0 else f"failed fail={report.count('FAIL')} warn={report.count('WARN')}"
    proofs = proofs_file(bundle.root, bundle.slug)
    inputs = [bundle.rel(bundle.spec), bundle.rel(bundle.tasks), *(bundle.rel(doc) for doc in bundle.tests), report.data.get("review"), report.data.get("security")]
    if proofs.is_file():
        inputs.append(proofs.relative_to(bundle.root).as_posix())
    digest = (report.data.get("fingerprint") or {}).get("digest")
    record(bundle.root, "VERIFICATION_COMPLETED", f"validate_verification {bundle.slug}", result, bundle.slug, "orchestrator", not args.no_record,
           node="gate", inputs=inputs, fingerprint=digest)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
