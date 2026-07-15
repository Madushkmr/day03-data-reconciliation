#!/usr/bin/env python3
"""
cli.py — command-line entry point for the Data Quality & Reconciliation
Pipeline.

Subcommands mirror the four pipeline stages:
    validate   — run per-source data quality checks
    reconcile   — cross-check two sources against each other
    report      — run validate + reconcile and write a Markdown/CSV report
    run          — alias for report (full pipeline, default)

Usage:
    python cli.py run --config config.yaml
    python cli.py validate --config config.yaml
    python cli.py reconcile --config config.yaml
    python cli.py report --config config.yaml --out output/report.md
"""

import argparse
import os
import sys

from pipeline.config import ConfigError, load_config
from pipeline.ingest import IngestError, load_all_sources
from pipeline.reconcile import reconcile_from_config
from pipeline.report import build_markdown_report, write_issues_csv
from pipeline.validate import validate_all


def cmd_validate(args):
    config = load_config(args.config)
    sources = load_all_sources(config)
    results = validate_all(sources, config)

    total = 0
    for name, issues in results.items():
        print(f"[{name}] {len(issues)} issue(s)")
        for issue in issues:
            print(f"  - {issue['rule']}: {issue['message']} (row key: {issue['row_key']})")
        total += len(issues)

    print(f"\nTotal validation issues: {total}")
    return 1 if total > 0 else 0


def cmd_reconcile(args):
    config = load_config(args.config)
    if "reconciliation" not in config:
        print("No 'reconciliation' section in config; nothing to reconcile.")
        return 0

    sources = load_all_sources(config)
    result = reconcile_from_config(sources, config)

    print(f"Matched: {len(result['matched'])}")
    print(f"Mismatched: {len(result['mismatched'])}")
    print(f"Missing in {result['secondary_source']}: {len(result['missing_in_secondary'])}")
    print(f"Missing in {result['primary_source']}: {len(result['missing_in_primary'])}")

    has_issues = result["mismatched"] or result["missing_in_secondary"] or result["missing_in_primary"]
    return 1 if has_issues else 0


def cmd_report(args):
    config = load_config(args.config)
    sources = load_all_sources(config)
    validation_results = validate_all(sources, config)

    reconciliation_result = None
    if "reconciliation" in config:
        reconciliation_result = reconcile_from_config(sources, config)

    markdown = build_markdown_report(validation_results, reconciliation_result)

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Markdown report written to {args.out}")

    csv_path = args.out.rsplit(".", 1)[0] + "_issues.csv"
    write_issues_csv(validation_results, reconciliation_result, csv_path)
    print(f"Issues CSV written to {csv_path}")

    print("\n" + markdown)

    total_validation_issues = sum(len(v) for v in validation_results.values())
    has_recon_issues = reconciliation_result and (
        reconciliation_result["mismatched"]
        or reconciliation_result["missing_in_secondary"]
        or reconciliation_result["missing_in_primary"]
    )
    return 1 if (total_validation_issues > 0 or has_recon_issues) else 0


def build_parser():
    parser = argparse.ArgumentParser(description="Data Quality & Reconciliation Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to the pipeline config file (default: config.yaml)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="Run data quality checks on all configured sources")
    subparsers.add_parser("reconcile", help="Cross-check the two reconciliation sources against each other")

    report_parser = subparsers.add_parser("report", help="Run the full pipeline and write a report")
    report_parser.add_argument("--out", default="output/report.md", help="Path to write the Markdown report (default: output/report.md)")

    run_parser = subparsers.add_parser("run", help="Alias for 'report' (runs the full pipeline)")
    run_parser.add_argument("--out", default="output/report.md", help="Path to write the Markdown report (default: output/report.md)")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            return cmd_validate(args)
        elif args.command == "reconcile":
            return cmd_reconcile(args)
        elif args.command in ("report", "run"):
            return cmd_report(args)
    except (ConfigError, IngestError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
