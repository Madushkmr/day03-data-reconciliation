"""
reconcile.py — stage 3 of the pipeline: cross-source reconciliation.

Compares two sources (e.g. a sales system export and a finance system
export that should agree on the same orders) by a shared key column.
Flags:
    missing_in_secondary — rows present in the primary source but absent from the secondary
    missing_in_primary   — rows present in the secondary source but absent from the primary
    mismatched            — rows present in both but whose compared columns differ by more
                             than the configured tolerance
    matched                — rows present in both and within tolerance on every compared column

This is the classic BI "do these two systems agree?" check — useful
whenever two teams / systems report on the same underlying events
(orders, transactions, inventory counts) and drift needs to be caught
before it reaches a dashboard.
"""


def reconcile(primary_df, secondary_df, primary_key, secondary_key, compare_columns, tolerance=0.0):
    # Duplicate keys within a single source are a data-quality problem in
    # their own right (validate.py's 'unique' rule catches them). For
    # reconciliation purposes we keep the first occurrence of each key so a
    # dirty source can't crash the comparison — the duplicate itself still
    # shows up in the validation report.
    primary_indexed = primary_df.drop_duplicates(subset=primary_key, keep="first").set_index(primary_key, drop=False)
    secondary_indexed = secondary_df.drop_duplicates(subset=secondary_key, keep="first").set_index(secondary_key, drop=False)

    primary_keys = set(primary_indexed.index)
    secondary_keys = set(secondary_indexed.index)

    missing_in_secondary = sorted(primary_keys - secondary_keys, key=str)
    missing_in_primary = sorted(secondary_keys - primary_keys, key=str)
    shared_keys = sorted(primary_keys & secondary_keys, key=str)

    matched = []
    mismatched = []

    for key in shared_keys:
        p_row = primary_indexed.loc[key]
        s_row = secondary_indexed.loc[key]
        diffs = {}
        for col in compare_columns:
            if col not in p_row or col not in s_row:
                continue
            p_val = p_row[col]
            s_val = s_row[col]
            try:
                if abs(float(p_val) - float(s_val)) > tolerance:
                    diffs[col] = {"primary": p_val, "secondary": s_val}
            except (TypeError, ValueError):
                if p_val != s_val:
                    diffs[col] = {"primary": p_val, "secondary": s_val}

        if diffs:
            mismatched.append({"key": key, "diffs": diffs})
        else:
            matched.append(key)

    return {
        "matched": matched,
        "mismatched": mismatched,
        "missing_in_secondary": missing_in_secondary,
        "missing_in_primary": missing_in_primary,
    }


def reconcile_from_config(sources, config):
    recon_cfg = config["reconciliation"]
    primary_name = recon_cfg["primary_source"]
    secondary_name = recon_cfg["secondary_source"]

    primary_df = sources[primary_name]
    secondary_df = sources[secondary_name]
    primary_key = config["sources"][primary_name]["key"]
    secondary_key = config["sources"][secondary_name]["key"]
    compare_columns = recon_cfg["compare_columns"]
    tolerance = recon_cfg.get("tolerance", 0.0)

    result = reconcile(primary_df, secondary_df, primary_key, secondary_key, compare_columns, tolerance)
    result["primary_source"] = primary_name
    result["secondary_source"] = secondary_name
    return result
