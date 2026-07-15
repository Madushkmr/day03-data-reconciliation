"""
ingest.py — stage 1 of the pipeline: load a configured source into a
pandas DataFrame.

Kept deliberately thin (just CSV loading + existence checks) so the
validate/reconcile stages can work against a plain DataFrame no
matter where the data originally came from. Swapping in a database or
API source later only means changing this module.
"""

import os

import pandas as pd


class IngestError(Exception):
    pass


def load_source(name, config):
    """Load a single named source (as declared in the config) into a DataFrame."""
    if name not in config["sources"]:
        raise IngestError(f"Unknown source '{name}'.")

    source_cfg = config["sources"][name]
    path = source_cfg["path"]

    if not os.path.exists(path):
        raise IngestError(f"Source file not found for '{name}': {path}")

    df = pd.read_csv(path)
    return df


def load_all_sources(config):
    """Load every source declared in the config. Returns {name: DataFrame}."""
    return {name: load_source(name, config) for name in config["sources"]}
