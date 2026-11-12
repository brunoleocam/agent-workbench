"""Structural validation of a traceable specification (REQ, AC, ADR links, approval).

Checks structure only. Whether a business rule makes sense stays with the planner, the reviewer, and the user.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import (  # noqa: E402
    ConfigError,
    Document,
    Report,
    add_common_args,
    artifact_path,
    config_error,
    ids_in,
    inside,
    load_document,
    project_root,
    record,
    resolve_layout,
)

SPEC_STATUS = {"draft", "review", "approved", "superseded"}
COMPLEXITY = ("XS", "S", "M", "L", "XL")
RISK_LEVELS = ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
ASSUMPTION_SECTIONS = ("assumptions", "premissas", "constraints", "restrições", "restricoes", "assumptions and constraints", "premissas e restrições")
QUESTION_SECTIONS = ("open questions", "ambiguities", "ambiguidades", "questões em aberto", "perguntas em aberto")
ADR_STEM = re.compile(r"^(?:adr[-_ ]?)?0*(\d+)(?:\b|[-_])", re.IGNORECASE)
EARS = re.compile(r"\b(SHALL|DEVE)\b")


def adr_numbers(root: Path, layout: dict) -> set[int]:
    found = set()
    for folder in layout["adr_dirs"]:
        path = root / folder
        if not path.is_dir():
            continue
        for item in path.glob("*.md"):
            match = ADR_STEM.match(item.stem)
            if match:
                found.add(int(match.group(1)))
    return found


def check_frontmatter(doc: Document, report: Report, require_approval: bool) -> None:
    meta = doc.frontmatter
    status = meta.get("status", "").lower()
    if not status:
        report.fail("status-missing", "Front matter has no status (draft, review, approved, superseded).")
    elif status not in SPEC_STATUS:
        report.fail("status-invalid", f"Unknown spec status '{status}'.")
    elif require_approval and status != "approved":
        report.fail("not-approved", f"Specification status is '{status}'; approval is required before planning.")
    elif status == "approved":
        report.ok("approved", "Specification is approved.")
    complexity = meta.get("complexity", "").upper()
    if complexity and complexity not in COMPLEXITY:
        report.fail("complexity-invalid", f"Unknown complexity '{complexity}' (XS, S, M, L, XL).")
    elif not complexity:
        report.warn("complexity-missing", "Front matter has no complexity.")
    risk = meta.get("security_risk", "").upper()
    triggers = [item.strip() for item in meta.get("security_triggers", "").split(",") if item.strip()]
    if risk and risk not in RISK_LEVELS:
        report.fail("risk-invalid", f"Unknown security_risk '{risk}' ({', '.join(RISK_LEVELS)}).")
    elif not risk and complexity in {"M", "L", "XL"}:
        report.warn("risk-missing", "Front matter has no security_risk for an M or larger change.")
    elif risk == "NONE" and triggers:
        report.warn("risk-inconsistent", f"security_risk is NONE but triggers are listed: {', '.join(triggers)}.")


def validate(doc: Document, root: Path, layout: dict, report: Report, require_approval: bool) -> None:
    check_frontmatter(doc, report, require_approval)
    reqs = doc.of_kind("REQ")
    acs = doc.of_kind("AC")
    if not reqs:
        report.fail("no-requirements", "No requirement found (heading starting with REQ-NNN).")
    if not acs:
        report.fail("no-acceptance", "No acceptance criterion found (heading starting with AC-NNN).")
    duplicated = [item for item, total in Counter(block.id for block in doc.blocks).items() if total > 1]
    for item in duplicated:
        lines = ", ".join(str(block.line) for block in doc.blocks if block.id == item)
        report.fail("duplicate-id", f"{item} is defined more than once (lines {lines}).", item)
    if reqs and not duplicated:
        report.ok("unique-ids", "Requirement and criterion identifiers are unique.")

    req_ids = {block.id for block in reqs}
    covered: set[str] = set()
    for ac in acs:
        linked = ac.ids("requirements", "REQ") + [item for item in ids_in(ac.title) if item.startswith("REQ-")]
        if not linked:
            report.fail("ac-unlinked", f"{ac.id} references no requirement.", ac.id)
        for item in linked:
            if item in req_ids:
                covered.add(item)
            else:
                report.fail("ac-unknown-req", f"{ac.id} references unknown requirement {item}.", ac.id)
        if not ac.text and not ac.get("expected"):
            report.fail("ac-empty", f"{ac.id} has no verifiable statement.", ac.id)
    if acs:
        report.ok("acceptance-found", f"{len(acs)} acceptance criteria found.")
    for req in reqs:
        if not req.text:
            report.fail("req-empty", f"{req.id} has no statement.", req.id)
        if req.id not in covered:
            report.warn("req-without-ac", f"{req.id} has no linked acceptance criterion.", req.id)
    ears = sum(1 for req in reqs if EARS.search(req.text))
    if reqs:
        report.info("ears", f"{ears}/{len(reqs)} requirements use EARS keywords (recommended for behavior, not mandatory).")

    if doc.section_lines(ASSUMPTION_SECTIONS) is None:
        report.warn("no-assumptions", "No Assumptions or Constraints section.")
    questions = doc.section_lines(QUESTION_SECTIONS)
    if questions is not None:
        open_items = [line for line in questions if re.match(r"^\s*[-*]\s+\[ \]", line)]
        if open_items and doc.frontmatter.get("status", "").lower() == "approved":
            report.warn("open-questions", f"Approved specification still has {len(open_items)} open question(s).")
        elif open_items:
            report.info("open-questions", f"{len(open_items)} open question(s) documented.")

    defined = {block.id for block in doc.blocks}
    mentioned: dict[str, int] = {}
    for number, line in enumerate(doc.lines, start=1):
        for item in ids_in(line):
            mentioned.setdefault(item, number)
    for item, number in sorted(mentioned.items()):
        if item.startswith(("REQ-", "AC-")) and item not in defined:
            report.warn("undefined-ref", f"{item} is mentioned (line {number}) but not defined in this spec.", item)
    known_adrs = adr_numbers(root, layout)
    for item in sorted(i for i in mentioned if i.startswith("ADR-")):
        if int(item.split("-")[1]) not in known_adrs:
            report.warn("adr-missing", f"{item} is cited but no ADR file was found in {', '.join(layout['adr_dirs'])}.", item)
    report.data["counts"] = {"requirements": len(reqs), "acceptance": len(acs), "ears": ears}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the structure of a traceable specification.")
    add_common_args(parser)
    parser.add_argument("--spec", help="spec path relative to the root (overrides --feature)")
    parser.add_argument("--require-approval", action="store_true", help="fail unless status is approved")
    args = parser.parse_args()
    try:
        root = project_root(args.root)
        layout = resolve_layout(root)
        path = artifact_path(root, args.spec, layout, "specs_dir", args.feature)
        if path is None:
            raise ConfigError("Pass --feature <slug> or --spec <path>.")
        doc = load_document(inside(root, path))
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    report = Report("Specification validation", strict=args.strict)
    report.data["spec"] = path.relative_to(root).as_posix()
    report.ok("structure", f"Specification parsed: {report.data['spec']}.")
    validate(doc, root, layout, report, args.require_approval)
    code = report.emit(args.json)
    result = "passed" if code == 0 else f"failed fail={report.count('FAIL')} warn={report.count('WARN')}"
    record(root, "SPEC_VALIDATION_COMPLETED", f"validate_spec {report.data['spec']}", result, args.feature or path.stem, "orchestrator", not args.no_record,
           node="spec_check", inputs=[report.data["spec"]])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
