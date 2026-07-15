"""
report.py — stage 4 of the pipeline: turn validation + reconciliation
results into a human-readable Markdown report and a machine-readable
CSV of every issue found.

Kept separate from validate.py/reconcile.py so the same underlying
results could later be rendered as HTML, sent to Slack, etc. without
touching the analysis logic.
"""

import csv
import os
from datetime import datetime, timezone


def _validation_summary(validation_results):
    lines = ["## Validation\n"]
    total_issues = sum(len(issues) for issues in validation_results.values())
    if total_issues == 0:
        lines.append("No validation issues found across any source.\n")
        return "\n".join(lines)

    for source, issues in validation_results.items():
        lines.append(f"### {source} ({len(issues)} issue(s))\n")
        if not issues:
            lines.append("- No issues.\n")
            continue
        for issue in issues:
            lines.append(f"- `{issue['rule']}` — {issue['message']} (row key: {issue['row_key']})")
        lines.append("")
    return "\n".join(lines)


def _reconciliation_summary(reconciliation_result):
    if not reconciliation_result:
        return ""

    r = reconciliation_result
    lines = ["## Reconciliation\n"]
    lines.append(f"Comparing **{r['primary_source']}** (primary) against **{r['secondary_source']}** (secondary).\n")
    lines.append(f"- Matched: {len(r['matched'])}")
    lines.append(f"- Mismatched: {len(r['mismatched'])}")
    lines.append(f"- Missing in {r['secondary_source']}: {len(r['missing_in_secondary'])}")
    lines.append(f"- Missing in {r['primary_source']}: {len(r['missing_in_primary'])}\n")

    if r["mismatched"]:
        lines.append("### Mismatched rows\n")
        for m in r["mismatched"]:
            diff_str = "; ".join(
                f"{col}: {d['primary']} vs {d['secondary']}" for col, d in m["diffs"].items()
            )
            lines.append(f"- key `{m['key']}`: {diff_str}")
        lines.append("")

    if r["missing_in_secondary"]:
        lines.append(f"### Present in {r['primary_source']} but missing from {r['secondary_source']}\n")
        for key in r["missing_in_secondary"]:
            lines.append(f"- `{key}`")
        lines.append("")

    if r["missing_in_primary"]:
        lines.append(f"### Present in {r['secondary_source']} but missing from {r['primary_source']}\n")
        for key in r["missing_in_primary"]:
            lines.append(f"- `{key}`")
        lines.append("")

    return "\n".join(lines)


def build_markdown_report(validation_results, reconciliation_result=None):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"# Data Quality & Reconciliation Report\n\nGenerated: {generated_at}\n"
    parts = [header, _validation_summary(validation_results)]
    if reconciliation_result:
        parts.append(_reconciliation_summary(reconciliation_result))
    return "\n".join(parts)


def write_issues_csv(validation_results, reconciliation_result, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "source", "rule", "column", "row_key", "message"])

        for source, issues in validation_results.items():
            for issue in issues:
                writer.writerow(["validation", issue["source"], issue["rule"], issue["column"], issue["row_key"], issue["message"]])

        if reconciliation_result:
            r = reconciliation_result
            for m in r["mismatched"]:
                diff_str = "; ".join(f"{col}: {d['primary']} vs {d['secondary']}" for col, d in m["diffs"].items())
                writer.writerow(["reconciliation", r["primary_source"], "mismatched", "", m["key"], diff_str])
            for key in r["missing_in_secondary"]:
                writer.writerow(["reconciliation", r["primary_source"], "missing_in_secondary", "", key, f"Present in {r['primary_source']}, missing in {r['secondary_source']}"])
            for key in r["missing_in_primary"]:
                writer.writerow(["reconciliation", r["secondary_source"], "missing_in_primary", "", key, f"Present in {r['secondary_source']}, missing in {r['primary_source']}"])

    return path
