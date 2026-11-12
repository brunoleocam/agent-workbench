"""Anti-AI-slop design lint for UI source files.

Reports P0 (blocking), P1, and P2 findings with file, line, rule, severity, message, and suggestion.
Heuristic: regular expressions over text, no CSS or JSX parser. Standard library only.

Exit codes: 0 without P0 findings, 1 with at least one P0, 2 on a usage error.
Suppress one rule on a line, or on the line after the comment:
    design-lint-disable P0-METRIC -- <reason>
A suppression without a reason is ignored and reported as P1-SUPPRESSION-NO-REASON.
"""

from __future__ import annotations

import argparse
import bisect
import colorsys
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

EXTENSIONS = {".html", ".htm", ".css", ".scss", ".jsx", ".tsx", ".vue", ".svelte"}
MARKUP = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".git"}
MAX_BYTES = 512 * 1024

AI_INDIGO = {"#6366f1", "#4f46e5", "#4338ca", "#3730a3", "#8b5cf6", "#7c3aed", "#a855f7"}
TAILWIND = {
    "indigo-400": "#818cf8", "indigo-500": "#6366f1", "indigo-600": "#4f46e5", "indigo-700": "#4338ca",
    "violet-400": "#a78bfa", "violet-500": "#8b5cf6", "violet-600": "#7c3aed", "violet-700": "#6d28d9",
    "purple-400": "#c084fc", "purple-500": "#a855f7", "purple-600": "#9333ea", "purple-700": "#7e22ce",
}
TW_FAMILY = {"blue": "blue", "sky": "blue", "cyan": "blue", "indigo": "blue", "violet": "purple", "purple": "purple", "fuchsia": "pink", "pink": "pink"}
# Tailwind default shades of the gradient families, so a declared brand color also clears its framework class.
TW_SHADES = {
    **TAILWIND,
    "blue-400": "#60a5fa", "blue-500": "#3b82f6", "blue-600": "#2563eb", "blue-700": "#1d4ed8",
    "sky-400": "#38bdf8", "sky-500": "#0ea5e9", "sky-600": "#0284c7", "sky-700": "#0369a1",
    "cyan-400": "#22d3ee", "cyan-500": "#06b6d4", "cyan-600": "#0891b2", "cyan-700": "#0e7490",
    "fuchsia-400": "#e879f9", "fuchsia-500": "#d946ef", "fuchsia-600": "#c026d3", "fuchsia-700": "#a21caf",
    "pink-400": "#f472b6", "pink-500": "#ec4899", "pink-600": "#db2777", "pink-700": "#be185d",
}
# CSS named colors in the purple, blue, cyan, and pink range.
NAMED = {
    "blue": "#0000ff", "navy": "#000080", "royalblue": "#4169e1", "dodgerblue": "#1e90ff", "deepskyblue": "#00bfff",
    "cyan": "#00ffff", "aqua": "#00ffff", "purple": "#800080", "violet": "#ee82ee", "indigo": "#4b0082",
    "blueviolet": "#8a2be2", "darkviolet": "#9400d3", "mediumpurple": "#9370db", "slateblue": "#6a5acd",
    "magenta": "#ff00ff", "fuchsia": "#ff00ff", "hotpink": "#ff69b4", "deeppink": "#ff1493",
}

ANY_HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_-])")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})", re.I)
HSL = re.compile(r"hsla?\(\s*(\d{1,3}(?:\.\d+)?)(?:deg)?[\s,]+(\d{1,3}(?:\.\d+)?)%[\s,]+(\d{1,3}(?:\.\d+)?)%", re.I)
NAMED_COLOR = re.compile(r"(?<![\w-])(" + "|".join(sorted(NAMED, key=len, reverse=True)) + r")(?![\w-])", re.I)
INDIGO_CLASS = re.compile(r"\b(?:bg|text|border|from|via|to|ring|fill|stroke|outline|shadow)-((?:indigo|violet|purple)-[4-7]00)\b")
GRADIENT = re.compile(r"(?:linear|radial|conic)-gradient\(([^;{}]{0,600})\)", re.I)
# Bounded window: an unbounded lazy scan to the end of the line is quadratic on minified CSS.
TW_GRADIENT = re.compile(r"\bfrom-([a-z]+-\d{2,3})\b[^\"'`\n{};<>]{0,200}?\bto-([a-z]+-\d{2,3})\b")
CLIP_TEXT = re.compile(r"background-clip\s*:\s*text|backgroundClip\s*:\s*[\"']text|\bbg-clip-text\b", re.I)
# Emoji presentation ranges; the check, cross, and ballot dingbats (U+2713 to U+2718) are ordinary UI glyphs.
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-✒✙-➿⭐⭕]")
TAG_INNER = re.compile(r"<(h[1-6]|button|li)\b[^>]{0,500}>(.{0,400}?)</\1\s*>", re.I | re.S)
ICON_ELEMENT = re.compile(
    r"<(\w+)\b[^>]{0,500}?\bclass(?:Name)?\s*=\s*(?:[\"'][^\"']{0,300}icon[^\"']{0,300}[\"']|\{[^{}]{0,300}icon[^{}]{0,300}\})[^>]{0,500}>([^<]{0,200})",
    re.I,
)
CSS_BLOCK = re.compile(r"\{([^{}]*)\}")
SIDE_BORDER = re.compile(
    r"(?:border-(?:left|right|inline-start|inline-end)|border(?:Left|Right|InlineStart|InlineEnd))"
    r"\s*:\s*[\"'`]?(\d+)px\s+solid\s+(?!transparent)",
)
RADIUS = re.compile(r"border-radius|borderRadius")
# Class strings: quoted, or a {...} expression such as cn("...", "...") or clsx(...).
CLASS_ATTR = re.compile(r"\bclass(?:Name)?\s*=\s*(?:\"([^\"]{0,1000})\"|'([^']{0,1000})'|\{([^{}]{0,1000})\})")
TW_SIDE = re.compile(r"\bborder-[lrse]-(?:[2-8]|\[\d+px\])(?![\w-])")
TW_ROUNDED = re.compile(r"\brounded(?!-none)(?:-[\w\[\]]+)?(?![\w-])")
TW_MOTION = re.compile(r"\b(?:animate-[a-z]+|transition(?:-[a-z]+)?)(?![\w-])")
FILLER = re.compile(r"lorem ipsum|\bfeature (?:one|two|three)\b|placeholder text|sample content|\bjohn doe\b|\bjane doe\b|(?<![\w./-])acme(?![\w-])", re.I)
METRIC = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?[x×]\s+(?:faster|better|more productive|more efficient|mais r[aá]pido|melhor|mais produtivo)\b"
    r"|\b(?:9\d|100)(?:[.,]\d+)?\s?%\s+(?:de\s+)?(?:uptime|availability|disponibilidade)\b"
    r"|\b(?:trusted by|used by|loved by|join|usado por|confiado por|mais de|over)\s+(?:\d{2,}[\d.,]*|\d+[.,]\d+)\s?(?:k|m|mil|milh[oõ]es)?\+?\s+(?:de\s+)?"
    r"(?:teams|companies|users|developers|customers|businesses|empresas|usu[aá]rios|times|clientes|desenvolvedores)\b",
    re.I,
)
CDN = re.compile(r"(?:images\.)?unsplash\.com|placehold\.co|placekitten\.com|picsum\.photos|via\.placeholder\.com", re.I)
# The reason needs a space after "--", so the "-->" that closes an HTML comment is never read as a reason.
SUPPRESS = re.compile(r"design-lint-disable\s+([A-Z0-9,\s-]+?)(?:\s+--\s+(\S.*?))?\s*(?:\*/|-->|\}|$)")
COMMENT_END = re.compile(r"\s*(?:\*/|-->|\})+\s*$")
RULE_ID = re.compile(r"P[012]-[A-Z-]+")


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str
    message: str
    suggestion: str


class Source:
    """One file's text with offset-to-line lookup."""

    def __init__(self, display: str, suffix: str, text: str, is_tokens: bool = False) -> None:
        self.display = display
        self.suffix = suffix
        self.text = text
        self.is_tokens = is_tokens
        self.starts = [0] + [index + 1 for index, char in enumerate(text) if char == "\n"]
        self.findings: list[Finding] = []

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset)

    def add(self, offset: int, rule: str, message: str, suggestion: str) -> None:
        self.findings.append(Finding(self.display, self.line(offset), rule, rule[:2], message, suggestion))


def norm_hex(value: str) -> str:
    value = value.lower()
    if len(value) == 4:
        value = "#" + "".join(char * 2 for char in value[1:])
    return value


def hue(value: str) -> float | None:
    """Hue in degrees for a saturated, mid-lightness color; None for neutrals."""
    value = norm_hex(value)
    red, green, blue = (int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))
    shade, light, saturation = colorsys.rgb_to_hls(red, green, blue)
    if saturation < 0.3 or light < 0.15 or light > 0.92:
        return None
    return shade * 360


TOKEN_DECLARATION = re.compile(r"--[\w-]+\s*:\s*([^;\n]+)")
SECTION = re.compile(r"^## (\d+)\.", re.M)


def to_hex(red: float, green: float, blue: float) -> str:
    return "#" + "".join(f"{max(0, min(255, round(value))):02x}" for value in (red, green, blue))


def stop_colors(text: str) -> list[str]:
    """Every color in a gradient's arguments as hex: hex literals, rgb(), hsl(), and named colors."""
    found = [norm_hex(item) for item in ANY_HEX.findall(text)]
    found += [to_hex(*(int(value) for value in match)) for match in RGB.findall(text)]
    for shade, saturation, light in HSL.findall(text):
        red, green, blue = colorsys.hls_to_rgb(float(shade) / 360, float(light) / 100, float(saturation) / 100)
        found.append(to_hex(red * 255, green * 255, blue * 255))
    found += [NAMED[name.lower()] for name in NAMED_COLOR.findall(text)]
    return found


def design_sections(text: str) -> dict[str, str]:
    marks = list(SECTION.finditer(text))
    return {mark.group(1): text[mark.start():marks[index + 1].start() if index + 1 < len(marks) else len(text)] for index, mark in enumerate(marks)}


def declared_colors(design: Path | None = None, tokens: Path | None = None) -> set[str]:
    """Brand colors: custom-property values in the tokens, and the color section of DESIGN.md.

    Anything else in DESIGN.md is prose, including section 9, which lists the forbidden defaults.
    """
    found: set[str] = set()
    if tokens and tokens.is_file():
        for value in TOKEN_DECLARATION.findall(tokens.read_text(encoding="utf-8", errors="replace")):
            found |= {norm_hex(item) for item in ANY_HEX.findall(value)}
    if design and design.is_file():
        sections = design_sections(design.read_text(encoding="utf-8", errors="replace"))
        found |= {norm_hex(item) for item in ANY_HEX.findall(sections.get("2", ""))}
        for number, body in sections.items():
            if number != "9":
                for value in TOKEN_DECLARATION.findall(body):
                    found |= {norm_hex(item) for item in ANY_HEX.findall(value)}
    return found


def class_value(match: re.Match) -> str:
    return match.group(1) or match.group(2) or match.group(3) or ""


def check_p0(src: Source, allowed: set[str]) -> None:
    text = src.text
    for match in ANY_HEX.finditer(text):
        value = norm_hex(match.group())
        if value in AI_INDIGO and value not in allowed:
            src.add(match.start(), "P0-INDIGO", f"Default Tailwind indigo/violet {value} used as a color.", "Use the accent token from DESIGN.md, for example var(--color-accent).")
    for match in INDIGO_CLASS.finditer(text):
        if TAILWIND[match.group(1)] not in allowed:
            src.add(match.start(), "P0-INDIGO", f"Default Tailwind class {match.group()} used as a color.", "Use the accent token from DESIGN.md instead of the framework default.")
    for match in GRADIENT.finditer(text):
        stops = stop_colors(match.group(1))
        hues = [value for value in (hue(item) for item in stops) if value is not None and 180 <= value < 345]
        if len(hues) >= 2 and max(hues) - min(hues) >= 20 and not set(stops) <= allowed:
            src.add(match.start(), "P0-GRADIENT", "Purple, blue, cyan, or pink two-stop gradient.", "Use a flat surface from the tokens and let type carry the section.")
    for match in TW_GRADIENT.finditer(text):
        first_class, last_class = match.group(1), match.group(2)
        first, last = TW_FAMILY.get(first_class.split("-")[0]), TW_FAMILY.get(last_class.split("-")[0])
        if not (first and last) or first_class.split("-")[0] == last_class.split("-")[0]:
            continue
        if TW_SHADES.get(first_class) in allowed and TW_SHADES.get(last_class) in allowed:
            continue
        src.add(match.start(), "P0-GRADIENT", f"Framework gradient {first_class} to {last_class}.", "Use a flat surface from the tokens and let type carry the section.")
    for match in CLIP_TEXT.finditer(text):
        src.add(match.start(), "P0-GRADIENT", "Gradient text (background-clip: text).", "Use a solid token color for text.")
    for match in CSS_BLOCK.finditer(text):
        body = match.group(1)
        side = SIDE_BORDER.search(body)
        if side and int(side.group(1)) >= 2 and RADIUS.search(body):
            src.add(match.start(1) + side.start(), "P0-SIDE-STRIPE", "Rounded card with a colored side border.", "Drop either the side border or the radius.")
    if src.suffix in MARKUP:
        for match in CLASS_ATTR.finditer(text):
            classes = class_value(match)
            if TW_SIDE.search(classes) and TW_ROUNDED.search(classes):
                src.add(match.start(), "P0-SIDE-STRIPE", "Rounded card with a colored side border.", "Drop either the side border or the radius.")
        flagged: set[int] = set()
        for regex in (TAG_INNER, ICON_ELEMENT):
            for match in regex.finditer(text):
                emoji = EMOJI.search(match.group(2) or "")
                offset = match.start(2) + emoji.start() if emoji else -1
                if emoji and offset not in flagged:
                    flagged.add(offset)
                    src.add(offset, "P0-EMOJI-ICON", f"Emoji used as an icon inside <{match.group(1)}>.", "Use a monoline SVG icon with currentColor, or remove it.")
        for match in FILLER.finditer(text):
            src.add(match.start(), "P0-FILLER", f"Filler text '{match.group()}'.", "Write real content from design/brief.md, or design a labelled empty state.")
        for match in METRIC.finditer(text):
            src.add(match.start(), "P0-METRIC", f"Unsourced marketing metric '{match.group()}'.", "Use a real, sourced number, or suppress with design-lint-disable P0-METRIC -- <source>.")
    for match in CDN.finditer(text):
        src.add(match.start(), "P0-PLACEHOLDER-CDN", f"Placeholder image CDN '{match.group()}'.", "Use a local asset or a labelled placeholder block.")


COLOR_FN = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lch|lab)\(", re.I)
TOKEN_SCOPE = re.compile(r"(?::root|@theme)[^{]*\{[^{}]*\}")
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}\n]+)|fontFamily\s*:\s*[\"'`]([^\"'`]+)", re.I)
TRANSITION_ALL = re.compile(r"transition\s*:\s*[\"'`]?all\b|\btransition-all\b", re.I)
OUTLINE_NONE = re.compile(r"outline\s*:\s*[\"'`]?(?:none|0)\b|\boutline-none\b", re.I)
FOCUS_VISIBLE = re.compile(r":focus-visible|focus-visible:")
# CSS and CSS-in-JS motion; a bare "transition" counts only inside a class string (see check_p1_p2).
MOTION = re.compile(r"@keyframes|\banimation\s*:|\btransition\s*:")
REDUCED = re.compile(r"prefers-reduced-motion|motion-reduce:|motion-safe:")
ACCENT = re.compile(r"var\(--(?:color-)?accent\)|\b(?:bg|text|border)-accent\b")
HOVER_SCALE = re.compile(r"\bhover:scale-\d+\b|:hover\s*\{[^}]*transform\s*:\s*scale\(")
KEYWORD_VALUES = ("var(", "inherit", "initial", "unset")
# Family tokens such as --font-display; size, weight, and spacing tokens share the prefix and are skipped.
FONT_TOKEN = re.compile(r"--font-(?![\w-]*(?:size|weight|leading|tracking|line|scale|step))[\w-]+\s*:\s*([^;}\n]+)", re.I)


def token_spans(text: str) -> list[tuple[int, int]]:
    return [match.span() for match in TOKEN_SCOPE.finditer(text)]


def in_spans(offset: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in spans)


def color_context(text: str, start: int) -> bool:
    """A hex is a color when it is a declaration value or a quoted or bracketed string, not a link, an SVG reference, or prose."""
    before = text[max(0, start - 12):start].lower()
    if "href" in before or before.endswith("url("):
        return False
    previous = text[:start].rstrip(" \t")[-1:]
    if previous in {":", ",", "(", "[", "\"", "'", "`"}:
        return True
    segment_start = max(text.rfind(";", 0, start), text.rfind("{", 0, start), text.rfind("\n", 0, start))
    return ":" in text[segment_start + 1:start] and previous not in {"", ">"}


def check_p1_p2(src: Source) -> None:
    text = src.text
    spans = token_spans(text)
    p0_lines = {item.line for item in src.findings if item.rule == "P0-INDIGO"}
    if not src.is_tokens:
        for match in ANY_HEX.finditer(text):
            if in_spans(match.start(), spans) or src.line(match.start()) in p0_lines or not color_context(text, match.start()):
                continue
            src.add(match.start(), "P1-RAW-COLOR", f"Literal color {match.group()} outside the tokens.", "Reference a color token, for example var(--color-ink).")
        for match in COLOR_FN.finditer(text):
            if in_spans(match.start(), spans) or src.line(match.start()) in p0_lines:
                continue
            src.add(match.start(), "P1-RAW-COLOR", f"Literal color {match.group().rstrip('(')} outside the tokens.", "Reference a color token, for example var(--color-ink).")
        for match in FONT_FAMILY.finditer(text):
            value = (match.group(1) or match.group(2) or "").strip()
            if in_spans(match.start(), spans) or value.startswith(KEYWORD_VALUES):
                continue
            src.add(match.start(), "P1-FONT-LITERAL", f"Literal font-family {value[:40]}.", "Use var(--font-display) or var(--font-body).")
    for match in TRANSITION_ALL.finditer(text):
        src.add(match.start(), "P1-TRANSITION-ALL", "transition: all animates every property.", "List the properties, for example transition: background-color 120ms ease-out.")
    if not FOCUS_VISIBLE.search(text):
        for match in OUTLINE_NONE.finditer(text):
            src.add(match.start(), "P1-OUTLINE-NONE", "Focus outline removed with no :focus-visible style in this file.", "Add a :focus-visible outline of at least 2px.")
    motion_at = [match.start() for match in MOTION.finditer(text)][:1]
    if not motion_at and src.suffix in MARKUP:
        motion_at = [match.start() for match in CLASS_ATTR.finditer(text) if TW_MOTION.search(class_value(match))][:1]
    if motion_at and not REDUCED.search(text):
        src.add(motion_at[0], "P1-NO-REDUCED-MOTION", "Motion without a prefers-reduced-motion fallback in this file.", "Add @media (prefers-reduced-motion: reduce) that removes or shortens the motion.")
    accents = list(ACCENT.finditer(text))
    if len(accents) > 6:
        src.add(accents[6].start(), "P2-ACCENT-OVERUSE", f"Accent used {len(accents)} times in one file.", "Keep the accent for the one or two things that must stand out.")
    scales = list(HOVER_SCALE.finditer(text))
    if len(scales) > 3:
        src.add(scales[3].start(), "P2-UNIFORM-HOVER-SCALE", f"The same hover scale on {len(scales)} elements.", "Give hover feedback that fits each element; reserve scale for one.")


def apply_suppressions(src: Source) -> None:
    allowed: dict[int, set[str]] = {}
    for number, line in enumerate(src.text.splitlines(), start=1):
        match = SUPPRESS.search(line)
        if not match:
            continue
        ids = set(RULE_ID.findall(match.group(1)))
        if not COMMENT_END.sub("", match.group(2) or "").strip():
            src.findings.append(Finding(src.display, number, "P1-SUPPRESSION-NO-REASON", "P1", "design-lint-disable without a reason is ignored.", "Add the reason after --, for example: design-lint-disable P0-METRIC -- SLA in the contract."))
            continue
        allowed.setdefault(number, set()).update(ids)
        allowed.setdefault(number + 1, set()).update(ids)
    src.findings = [item for item in src.findings if item.rule not in allowed.get(item.line, set())]


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            if path.suffix.lower() in EXTENSIONS:
                yield path
            continue
        for folder, dirs, files in os.walk(path):
            dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
            for name in sorted(files):
                if Path(name).suffix.lower() in EXTENSIONS:
                    yield Path(folder) / name


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def lint_paths(paths: list[Path], design: Path | None = None, tokens: Path | None = None, notes: list[str] | None = None) -> list[Finding]:
    """Lint every UI file under paths. Files that were not read go to notes as "skipped (...)" or "unreadable (...)"."""
    notes = notes if notes is not None else []
    allowed = declared_colors(design, tokens)
    token_file = tokens.resolve() if tokens and tokens.is_file() else None
    sources: list[Source] = []
    for path in iter_files(paths):
        try:
            if path.stat().st_size > MAX_BYTES:
                notes.append(f"{display(path)}: skipped (larger than {MAX_BYTES // 1024} KB)")
                continue
            text = read_source(path)
        except OSError as error:
            notes.append(f"{display(path)}: unreadable ({error.__class__.__name__})")
            continue
        src = Source(display(path), path.suffix.lower(), text, path.resolve() == token_file)
        check_p0(src, allowed)
        check_p1_p2(src)
        sources.append(src)
    check_across_files(sources)
    for src in sources:
        apply_suppressions(src)
    findings = [item for src in sources for item in src.findings]
    return sorted(findings, key=lambda item: (item.file, item.line, item.rule))


def first_family(value: str) -> str:
    return value.split(",")[0].strip().strip("\"'`").lower()


def font_scope(src: Source) -> str:
    """Each preview in design/directions/ is an alternative look, so it is its own scope; the rest is one product."""
    parts = Path(src.display).parts
    in_directions = any(parts[index:index + 2] == ("design", "directions") for index in range(len(parts) - 1))
    return src.display if in_directions else ""


def check_across_files(sources: list[Source]) -> None:
    """P1-FONT-COUNT: more than three font families across the scanned files of one scope."""
    scopes: dict[str, list[str]] = {}
    for src in sources:
        seen = scopes.setdefault(font_scope(src), [])
        declared = [(match.start(), match.group(1)) for match in FONT_TOKEN.finditer(src.text)]
        literal = [(match.start(), match.group(1) or match.group(2)) for match in FONT_FAMILY.finditer(src.text)]
        for offset, raw in sorted(declared + literal):
            value = (raw or "").strip()
            if value.startswith(KEYWORD_VALUES):
                continue
            family = first_family(value)
            if family and family not in seen:
                seen.append(family)
                if len(seen) == 4:
                    src.add(offset, "P1-FONT-COUNT", f"Fourth font family '{family}' ({', '.join(seen)}).", "Keep at most three families: display, body, and one outlier.")


def summary(findings: list[Finding]) -> dict[str, int]:
    return {level: sum(1 for item in findings if item.severity == level) for level in ("P0", "P1", "P2")}


def render_text(findings: list[Finding]) -> str:
    lines = [f"{item.file}:{item.line}: {item.severity} {item.rule} {item.message} Fix: {item.suggestion}" for item in findings]
    counts = summary(findings)
    lines.append(f"design lint: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anti-AI-slop design lint for UI source files.")
    parser.add_argument("paths", nargs="*", default=["."], help="files or folders (default: current folder)")
    parser.add_argument("--design", help="DESIGN.md whose colors are allowed (default: ./DESIGN.md when present)")
    parser.add_argument("--tokens", help="token stylesheet whose colors are allowed (default: ./design/tokens.css when present)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    paths = [Path(item) for item in args.paths]
    for given in (args.design, args.tokens):
        if given and not Path(given).is_file():
            print(f"error: {given} not found", file=sys.stderr)
            return 2
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(f"error: not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    design = Path(args.design) if args.design else Path("DESIGN.md")
    tokens = Path(args.tokens) if args.tokens else Path("design/tokens.css")
    notes: list[str] = []
    findings = lint_paths(paths, design if design.is_file() else None, tokens if tokens.is_file() else None, notes)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    for note in notes:
        print(note, file=sys.stderr)
    if args.format == "json":
        print(json.dumps({"findings": [asdict(item) for item in findings], "summary": summary(findings), "notes": notes}, ensure_ascii=True))
    else:
        print(render_text(findings))
    if summary(findings)["P0"]:
        return 1
    # A file that could not be read is a usage problem, not a clean result.
    return 2 if any("unreadable" in note for note in notes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
