#!/usr/bin/env python3
"""Read-only scientific R maintenance audit.

Separate objective observations, context-dependent review signals, and
evidence-backed risks. Never infer whether code was written by AI.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import re
from collections import defaultdict
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "archive",
    "archives",
    "backup",
    "backups",
    "deprecated",
    "generated",
    "renv",
    "temp",
    "tmp",
    "vendor",
}

COUNT_PATTERNS = {
    "cat_calls": re.compile(r"\bcat\s*\("),
    "message_calls": re.compile(r"\bmessage\s*\("),
    "trycatch_calls": re.compile(r"\btryCatch\s*\("),
    "manual_geom_calls": re.compile(r"\b(?:geom_segment|geom_text|geom_label|annotate)\s*\("),
    "function_defs": re.compile(r"<-\s*function\s*\("),
    "source_calls": re.compile(r"\bsource\s*\("),
    "hex_colours": re.compile(r"#[0-9A-Fa-f]{6}\b"),
    "numeric_xy_assignments": re.compile(
        r"\b(?:x|y|xmin|xmax|ymin|ymax|X_position|Y_position)\s*=\s*-?\d+(?:\.\d+)?"
    ),
}

ROLE_PATTERNS = {
    "read": re.compile(r"\b(?:read\.(?:csv|delim|table|tsv)|readRDS|fread)\s*\("),
    "statistics_or_model": re.compile(
        r"\b(?:adonis2|mantel|betadisper|permutest|wilcox\.test|t\.test|aov|anova|TukeyHSD|lm|glm|DESeq|cor)\s*\("
    ),
    "plot": re.compile(r"\b(?:ggplot|Heatmap|draw|pheatmap)\s*\("),
    "write": re.compile(r"\b(?:write\.(?:csv|table)|write_csv|write_tsv|saveRDS|ggsave|writeLines)\s*\("),
    "external_command": re.compile(r"\b(?:system|system2)\s*\("),
}

WRITE_FUNCTIONS = ("write.csv", "write.table", "write_csv", "write_tsv", "saveRDS", "writeLines")
READ_FUNCTIONS = ("read.csv", "read.delim", "read.table", "read_tsv", "readRDS", "fread")


def is_excluded(path: Path, root: Path, extra_patterns: list[str]) -> bool:
    relative = path.relative_to(root) if path != root else Path(path.name)
    if any(part.lower() in DEFAULT_EXCLUDED_DIRS for part in relative.parts[:-1]):
        return True
    relative_text = relative.as_posix()
    return any(fnmatch.fnmatch(relative_text, pattern) for pattern in extra_patterns)


def r_files(target: Path, extra_patterns: list[str]) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".r" else []
    return sorted(
        path
        for path in target.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".r"
        and not is_excluded(path, target, extra_patterns)
    )


def code_without_comment_lines(lines: list[str]) -> str:
    return "\n".join("" if line.lstrip().startswith("#") else line for line in lines)


def locations(lines: list[str], pattern: re.Pattern[str]) -> list[dict[str, object]]:
    return [
        {"line": number, "text": line.strip()}
        for number, line in enumerate(lines, 1)
        if not line.lstrip().startswith("#") and pattern.search(line)
    ]


def call_blocks(lines: list[str], function_names: tuple[str, ...]) -> list[dict[str, object]]:
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(name) for name in function_names) + r")\s*\(")
    blocks: list[dict[str, object]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.lstrip().startswith("#") or not pattern.search(line):
            index += 1
            continue
        start = index
        text_parts = [line]
        balance = line.count("(") - line.count(")")
        while balance > 0 and index + 1 < len(lines) and index - start < 30:
            index += 1
            text_parts.append(lines[index])
            balance += lines[index].count("(") - lines[index].count(")")
        blocks.append({"line": start + 1, "text": "\n".join(text_parts)})
        index += 1
    return blocks


def path_assignments(lines: list[str]) -> dict[str, dict[str, object]]:
    assignments: dict[str, dict[str, object]] = {}
    assignment_pattern = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_.]*)\s*<-\s*file\.path\s*\(")
    index = 0
    while index < len(lines):
        match = assignment_pattern.search(lines[index])
        if not match:
            index += 1
            continue
        start = index
        text_parts = [lines[index]]
        balance = lines[index].count("(") - lines[index].count(")")
        while balance > 0 and index + 1 < len(lines) and index - start < 20:
            index += 1
            text_parts.append(lines[index])
            balance += lines[index].count("(") - lines[index].count(")")
        assignments[match.group(1)] = {"line": start + 1, "text": "\n".join(text_parts)}
        index += 1
    return assignments


def add_signal(container: list[dict[str, object]], kind: str, detail: str, lines: list[int] | None = None) -> None:
    item: dict[str, object] = {"type": kind, "detail": detail}
    if lines:
        item["lines"] = sorted(set(lines))
    container.append(item)


def analyse_file(path: Path) -> tuple[dict[str, object], list[str], dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    code_text = code_without_comment_lines(lines)
    code_lines = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    counts = {name: len(pattern.findall(code_text)) for name, pattern in COUNT_PATTERNS.items()}
    roles = [name for name, pattern in ROLE_PATTERNS.items() if pattern.search(code_text)]
    observations: dict[str, object] = {
        "lines": len(lines),
        "nonblank_lines": sum(bool(line.strip()) for line in lines),
        "comment_lines": sum(line.lstrip().startswith("#") for line in lines),
        "long_lines_over_100": sum(len(line) > 100 for line in lines),
        "roles": roles,
        **counts,
    }
    review_signals: list[dict[str, object]] = []
    risks: list[dict[str, object]] = []

    cat_locs = locations(lines, COUNT_PATTERNS["cat_calls"])
    if len(cat_locs) >= 10:
        add_signal(review_signals, "heavy_progress_logging", "At least ten cat() calls; verify that logging explains decisions.", [x["line"] for x in cat_locs])

    try_locs = locations(lines, COUNT_PATTERNS["trycatch_calls"])
    if len(try_locs) >= 3:
        add_signal(review_signals, "broad_error_recovery", "Several tryCatch() blocks; verify that every caught error has a defined recovery.", [x["line"] for x in try_locs])

    # A coherent analysis commonly reads, prepares, tests, writes, and plots in one
    # self-contained script. Operation diversity alone is not mixed responsibility.
    # Reserve this heuristic for unusually large scripts that also orchestrate
    # external programs; scientific boundaries still require human review.
    if len(lines) > 500 and len(roles) >= 4 and "external_command" in roles:
        add_signal(review_signals, "possible_mixed_scientific_responsibilities", f"Very long script combines analysis roles and external orchestration: {', '.join(roles)}.")

    geometry_locs = locations(lines, COUNT_PATTERNS["manual_geom_calls"])
    coordinate_locs = locations(lines, COUNT_PATTERNS["numeric_xy_assignments"])
    embedded_layout = re.search(r"\b(?:node_positions|edge_coordinates|module_areas)\s*<-\s*data\.frame\s*\(", code_text)
    if embedded_layout and len(coordinate_locs) >= 8:
        add_signal(review_signals, "embedded_manual_layout", "Large manual layout appears embedded in executable code; consider an auditable layout table.", [x["line"] for x in coordinate_locs])
    elif len(geometry_locs) >= 10 and len(coordinate_locs) >= 10:
        add_signal(review_signals, "manual_geometry_stack", "Many manual geometry calls and numeric coordinates; verify that data or label changes do not require global retuning.", [x["line"] for x in geometry_locs])

    implicit_patterns = {
        "setwd": re.compile(r"\bsetwd\s*\("),
        "load": re.compile(r"(?<![A-Za-z0-9_.])load\s*\("),
        "save_image": re.compile(r"\bsave\.image\s*\("),
    }
    for kind, pattern in implicit_patterns.items():
        hits = locations(lines, pattern)
        if hits:
            add_signal(risks, f"implicit_state_{kind}", "Implicit working-directory or workspace state can make results non-reproducible.", [x["line"] for x in hits])

    assignments = path_assignments(lines)
    write_blocks = call_blocks(lines, WRITE_FUNCTIONS)
    read_blocks = call_blocks(lines, READ_FUNCTIONS)
    for variable, assignment in assignments.items():
        normalized = re.sub(r"\s+", "", str(assignment["text"]).lower())
        is_data_path = bool(re.search(r"[\"']data(?:/|[\"'])", normalized))
        is_final_path = "result/tables" in normalized or ('"result"' in normalized and '"tables"' in normalized)
        if is_data_path:
            for block in write_blocks:
                if re.search(rf"\b{re.escape(variable)}\b", str(block["text"])):
                    add_signal(risks, "write_to_data", f"A write call targets data-path variable `{variable}`.", [int(assignment["line"]), int(block["line"])])
        if is_final_path:
            for block in read_blocks:
                if re.search(rf"\b{re.escape(variable)}\b", str(block["text"])):
                    add_signal(risks, "read_from_final_tables", f"A downstream read uses final-table path variable `{variable}`.", [int(assignment["line"]), int(block["line"])])

    hardcoded_stat_pattern = re.compile(
        r"(?i)(?:label|title|subtitle|caption)\s*=.*[\"'][^\"']*(?:p\s*[=<>]\s*0?\.\d+|auc\s*=\s*\d|n\s*=\s*\d)"
    )
    stat_hits = locations(lines, hardcoded_stat_pattern)
    if stat_hits:
        add_signal(risks, "hardcoded_statistical_label", "A plot label appears to contain a typed statistical value.", [x["line"] for x in stat_hits])

    scientific_parameters: dict[str, str] = {}
    parameter_pattern = re.compile(
        r"^\s*([A-Za-z][A-Za-z0-9_.]*(?:cutoff|threshold|permutations|replicates)[A-Za-z0-9_.]*)\s*<-\s*([0-9]+(?:\.[0-9]+)?L?)\s*$",
        re.IGNORECASE,
    )
    for line in lines:
        match = parameter_pattern.match(line)
        if match:
            scientific_parameters[match.group(1)] = match.group(2)

    return {
        "file": str(path),
        "observations": observations,
        "review_signals": review_signals,
        "risks": risks,
    }, code_lines, scientific_parameters


def paired_kind(left: Path, right: Path) -> str:
    stems = f"{left.stem.lower()} {right.stem.lower()}"
    if "ck" in stems and "sc" in stems:
        return "paired_treatment_scripts"
    left_prefix = re.match(r"\d+", left.stem)
    right_prefix = re.match(r"\d+", right.stem)
    if left_prefix and right_prefix and left_prefix.group() == right_prefix.group():
        return "paired_panel_family"
    return "general_similarity"


def duplicate_pairs(
    code: dict[Path, list[str]],
    parameters: dict[Path, dict[str, str]],
    cutoff: float,
) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    paths = sorted(code)
    for index, left in enumerate(paths):
        for right in paths[index + 1 :]:
            matcher = difflib.SequenceMatcher(None, code[left], code[right], autojunk=False)
            ratio = matcher.ratio()
            if ratio < cutoff:
                continue
            blocks = [block for block in matcher.get_matching_blocks() if block.size >= 5]
            overlap = sum(block.size for block in blocks)
            segments = [
                {
                    "left_lines": [block.a + 1, block.a + block.size],
                    "right_lines": [block.b + 1, block.b + block.size],
                    "matching_lines": block.size,
                }
                for block in sorted(blocks, key=lambda item: item.size, reverse=True)[:5]
            ]
            common_parameters = sorted(set(parameters[left]) & set(parameters[right]))
            parameter_differences = {
                name: {"left": parameters[left][name], "right": parameters[right][name]}
                for name in common_parameters
                if parameters[left][name] != parameters[right][name]
            }
            pairs.append(
                {
                    "classification": "review_signal",
                    "left": str(left),
                    "right": str(right),
                    "pair_kind": paired_kind(left, right),
                    "similarity": round(ratio, 3),
                    "effective_matching_lines": overlap,
                    "left_code_lines": len(code[left]),
                    "right_code_lines": len(code[right]),
                    "largest_matching_segments": segments,
                    "scientific_parameter_differences": parameter_differences,
                    "interpretation": "Similarity alone does not require merging; inspect scientific independence and unintended drift.",
                }
            )
    return sorted(pairs, key=lambda item: (item["similarity"], item["effective_matching_lines"]), reverse=True)


def find_project_root(target: Path) -> Path:
    start = target if target.is_dir() else target.parent
    for candidate in [start, *start.parents]:
        if (candidate / "README.md").exists() or (candidate / ".git").exists():
            return candidate
    return start


def project_checks(project_root: Path, files: list[Path]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    signals: list[dict[str, object]] = []
    risks: list[dict[str, object]] = []
    root_occurrences: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    colour_occurrences: defaultdict[str, defaultdict[str, list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))

    root_pattern = re.compile(r"\bproject_root\s*<-\s*[\"']([^\"']+)[\"']")
    colour_pattern = re.compile(r"\b(CK|SC)\s*=\s*[\"'](#[0-9A-Fa-f]{6})[\"']")
    for path in files:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        for number, line in enumerate(lines, 1):
            root_match = root_pattern.search(line)
            if root_match:
                root_occurrences[root_match.group(1)].append({"file": str(path), "line": number})
            for label, colour in colour_pattern.findall(line):
                colour_occurrences[label][colour.upper()].append({"file": str(path), "line": number})

    for literal, hits in root_occurrences.items():
        if len(hits) > 1:
            signals.append({
                "type": "repeated_absolute_project_root",
                "detail": f"The same absolute project root occurs in {len(hits)} scripts: {literal}",
                "locations": hits,
            })

    for label, colours in colour_occurrences.items():
        if len(colours) > 1:
            signals.append({
                "type": "inconsistent_named_colour",
                "detail": f"Named treatment `{label}` has multiple colours: {', '.join(sorted(colours))}",
                "locations": colours,
            })

    artifact_hits = []
    for name in (".RData", ".Rhistory"):
        for path in project_root.rglob(name):
            artifact_hits.append(str(path))
    if artifact_hits:
        risks.append({
            "type": "implicit_workspace_artifact_present",
            "detail": "Workspace-history artifacts are present and can introduce hidden state or version-control noise.",
            "paths": sorted(artifact_hits),
        })

    readme = project_root / "README.md"
    if readme.exists():
        readme_text = readme.read_text(encoding="utf-8-sig", errors="replace")
        missing_locations: defaultdict[str, list[int]] = defaultdict(list)
        negative_context = re.compile(
            r"(?:当前)?(?:没有|不存在|未提供|无)|"
            r"(?:does\s+not\s+exist|doesn't\s+exist|not\s+present|no\s+.+(?:script|runner))",
            re.IGNORECASE,
        )
        for line_number, line in enumerate(readme_text.splitlines(), start=1):
            references = re.findall(r"`((?:scripts/)?[A-Za-z0-9_.-]+\.R)`", line)
            if not references or negative_context.search(line):
                continue
            for reference in references:
                candidate = (
                    project_root / reference
                    if reference.startswith("scripts/")
                    else project_root / "scripts" / reference
                )
                if not candidate.exists():
                    missing_locations[reference].append(line_number)
        missing = sorted(missing_locations)
        if missing:
            risks.append({
                "type": "readme_references_missing_scripts",
                "detail": "README references scripts that do not exist.",
                "paths": missing,
                "locations": [
                    {"reference": reference, "lines": missing_locations[reference]}
                    for reference in missing
                ],
            })
    return signals, risks


def build_report(target: Path, cutoff: float, exclude: list[str]) -> dict[str, object]:
    files = r_files(target, exclude)
    analyses: list[dict[str, object]] = []
    code: dict[Path, list[str]] = {}
    parameters: dict[Path, dict[str, str]] = {}
    for path in files:
        analysis, code_lines, scientific_parameters = analyse_file(path)
        analyses.append(analysis)
        code[path] = code_lines
        parameters[path] = scientific_parameters
    project_root = find_project_root(target)
    project_signals, project_risks = project_checks(project_root, files)
    return {
        "target": str(target.resolve()),
        "project_root": str(project_root.resolve()),
        "disclaimer": "Observations and review signals do not identify AI authorship or require refactoring by themselves.",
        "summary": {
            "r_files": len(files),
            "total_lines": sum(int(item["observations"]["lines"]) for item in analyses),
            "file_review_signals": sum(len(item["review_signals"]) for item in analyses),
            "file_risks": sum(len(item["risks"]) for item in analyses),
            "project_review_signals": len(project_signals),
            "project_risks": len(project_risks),
        },
        "project_review_signals": project_signals,
        "project_risks": project_risks,
        "files": analyses,
        "duplicate_pairs": duplicate_pairs(code, parameters, cutoff),
    }


def print_text(report: dict[str, object]) -> None:
    summary = report["summary"]
    print(report["disclaimer"])
    print(
        f"R files: {summary['r_files']} | lines: {summary['total_lines']} | "
        f"review signals: {summary['file_review_signals'] + summary['project_review_signals']} | "
        f"risks: {summary['file_risks'] + summary['project_risks']}"
    )
    for item in report["project_risks"]:
        print(f"RISK\tPROJECT\t{item['type']}\t{item['detail']}")
    for item in report["project_review_signals"]:
        print(f"SIGNAL\tPROJECT\t{item['type']}\t{item['detail']}")
    for file_item in report["files"]:
        for item in file_item["risks"]:
            print(f"RISK\t{file_item['file']}\t{item['type']}\tlines={item.get('lines', [])}\t{item['detail']}")
        for item in file_item["review_signals"]:
            print(f"SIGNAL\t{file_item['file']}\t{item['type']}\tlines={item.get('lines', [])}\t{item['detail']}")
    for pair in report["duplicate_pairs"]:
        print(
            f"DUP_SIGNAL\t{pair['similarity']:.3f}\tmatching={pair['effective_matching_lines']}\t"
            f"{pair['pair_kind']}\t{pair['left']}\t{pair['right']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="R file or directory to inspect")
    parser.add_argument("--duplicate-cutoff", type=float, default=0.70)
    parser.add_argument("--exclude", action="append", default=[], help="Relative glob to exclude; repeat as needed")
    parser.add_argument("--json", action="store_true", help="emit full JSON")
    args = parser.parse_args()
    if not args.target.exists():
        parser.error(f"target does not exist: {args.target}")
    if not 0 <= args.duplicate_cutoff <= 1:
        parser.error("--duplicate-cutoff must be between 0 and 1")
    report = build_report(args.target, args.duplicate_cutoff, args.exclude)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
