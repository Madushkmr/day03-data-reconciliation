"""
validate.py — stage 2 of the pipeline: run per-source data quality
checks against the rules declared in the config.

Each rule type returns a list of "issue" dicts with a consistent
shape (source, rule, column, row_key, message) so validate.py,
reconcile.py's output, and report.py can all be combined into one
issue list for the final report.

Supported rule types (all optional per source):
    required_columns  — columns that must exist in the DataFrame
    not_null          — columns that must not contain nulls
    unique             — columns whose values must not repeat
    numeric_range      — {column: {min, max}} bounds check
"""


def _issue(source, rule, column, row_key, message):
    return {
        "source": source,
        "rule": rule,
        "column": column,
        "row_key": row_key,
        "message": message,
    }


def validate_source(name, df, rules, key_column=None):
    """Run all configured rules for one source. Returns a list of issues."""
    issues = []

    required_columns = rules.get("required_columns", [])
    missing_columns = [c for c in required_columns if c not in df.columns]
    for col in missing_columns:
        issues.append(_issue(name, "required_columns", col, None, f"Column '{col}' is missing from source '{name}'."))

    # Rules below need the column to actually exist, so skip missing ones.
    present_columns = set(df.columns) - set(missing_columns)

    for col in rules.get("not_null", []):
        if col not in present_columns:
            continue
        null_rows = df[df[col].isna()]
        for idx, row in null_rows.iterrows():
            row_key = row[key_column] if key_column and key_column in df.columns else idx
            issues.append(_issue(name, "not_null", col, row_key, f"'{col}' is null."))

    for col in rules.get("unique", []):
        if col not in present_columns:
            continue
        dup_mask = df[col].duplicated(keep=False) & df[col].notna()
        for idx, row in df[dup_mask].iterrows():
            row_key = row[key_column] if key_column and key_column in df.columns else idx
            issues.append(_issue(name, "unique", col, row_key, f"Duplicate value '{row[col]}' in '{col}'."))

    for col, bounds in rules.get("numeric_range", {}).items():
        if col not in present_columns:
            continue
        lo = bounds.get("min")
        hi = bounds.get("max")
        numeric = df[col].apply(lambda v: isinstance(v, (int, float)))
        for idx, row in df[numeric].iterrows():
            value = row[col]
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                row_key = row[key_column] if key_column and key_column in df.columns else idx
                issues.append(
                    _issue(name, "numeric_range", col, row_key, f"'{col}' = {value} is outside [{lo}, {hi}].")
                )

    return issues


def validate_all(sources, config):
    """Validate every source that has rules configured. Returns {name: [issues]}."""
    all_rules = config.get("validation_rules", {})
    results = {}
    for name, df in sources.items():
        rules = all_rules.get(name, {})
        key_column = config["sources"][name].get("key")
        results[name] = validate_source(name, df, rules, key_column)
    return results
