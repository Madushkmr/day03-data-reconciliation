# Data Quality & Reconciliation Pipeline

Day 3 of a daily AI-app build series, focused on Business Intelligence use cases.

A config-driven, multi-stage pipeline that checks data quality within a source (missing columns, nulls, duplicates, out-of-range values) and reconciles two sources that are supposed to agree with each other (e.g. a sales system's order export vs. a finance system's posted-transactions export). Outputs a Markdown report and a CSV of every issue found.

## Why this is useful for BI work

Two of the most common (and most tedious) BI/data-eng tasks are: "does this data pass basic sanity checks?" and "do these two systems agree on the same numbers?" Both usually get done by hand in spreadsheets, repeatedly, right before a report ships. This pipeline automates both checks, driven entirely by a YAML config, so new sources or new rules can be added without touching the pipeline code — which matters once this kind of check needs to run on a schedule or across many source pairs.

## Architecture

```
day03-data-reconciliation/
  cli.py                    Command-line entry point (validate / reconcile / report / run)
  config.yaml                 Declares sources, reconciliation settings, and validation rules
  pipeline/
    __init__.py
    config.py                  Loads + sanity-checks config.yaml
    ingest.py                   Stage 1: loads each configured CSV source into a DataFrame
    validate.py                 Stage 2: per-source data quality checks (required columns, not-null, unique, numeric range)
    reconcile.py                 Stage 3: cross-source comparison by key column, with a numeric tolerance
    report.py                     Stage 4: renders Markdown report + writes an issues CSV
  sample_data/
    sales_export.csv              Synthetic "sales system" export (21 rows, includes a duplicate order_id and a null customer_id)
    finance_export.csv            Synthetic "finance system" export (19 rows; missing 2 orders present in sales, has 1 extra order, 2 amount mismatches)
  tests/
    test_validate.py               Unit tests for every validation rule type
    test_reconcile.py              Unit tests for matched/mismatched/missing classification
  requirements.txt
```

Pipeline flow: `ingest` loads each CSV named in `config.yaml` into a DataFrame -> `validate` runs the rules configured per source (required columns, not-null, uniqueness, numeric ranges) -> `reconcile` compares the two sources named under `reconciliation` by their key column, flagging rows that are missing from one side or whose compared columns differ by more than `tolerance` -> `report` combines both results into a Markdown report (`output/report.md`) and a flat issues CSV (`output/report_issues.csv`).

The sample data is seeded with deliberate problems so a first run demonstrates every rule: a duplicated `order_id` and a null `customer_id` in `sales_export.csv`; two orders missing from `finance_export.csv`; one order present only in `finance_export.csv`; and two orders whose `amount` disagrees between the two files.

## How to run

```bash
pip install -r requirements.txt

# Run the full pipeline (validate + reconcile + report)
python cli.py run

# Or run stages individually
python cli.py validate
python cli.py reconcile
python cli.py report --out output/report.md
```

The CLI exits with status 1 if any validation or reconciliation issues were found (0 if everything is clean), so it can be wired into a scheduled job or CI check.

## Tests

```bash
python -m pytest tests/ -v
```

Covers every validation rule type and every reconciliation outcome (matched, mismatched within/beyond tolerance, missing on either side).

## Next in this series

Day 1 was a single-script anomaly detector. Day 2 added a Flask web UI with a modular parser/db split. Day 3 steps up again: a config-driven, multi-stage pipeline (ingest -> validate -> reconcile -> report) with a proper CLI and a broader test suite — closer to how this kind of check would actually run in a scheduled BI job. Future days will keep escalating: persistent storage, dashboards, and eventually agentic multi-step workflows.
