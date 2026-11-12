"""Closing gate for a feature: every criterion tested, every required test proven on the current code,
independent review done, blocking findings resolved, accepted risks justified, and task states consistent."""

from __future__ import annotations

import argparse
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
    proofs_file,
    record,
    task_status,
    truthy,
    workspace_fingerprint,
)
from lib import redact  # noqa: E402

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
