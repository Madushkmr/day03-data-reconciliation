"""
config.py — loads and validates the pipeline's YAML config file.

The config declares every data source (path + reconciliation key),
the reconciliation settings (which two sources to compare, which
columns, and the numeric tolerance for "close enough" matches), and
per-source validation rules (required columns, not-null columns,
uniqueness, numeric ranges).

Keeping this in one config file (rather than hard-coding source paths
and rules in the pipeline code) is what makes the pipeline reusable
across different BI data-quality checks without touching Python.
"""

import os

import yaml


class ConfigError(Exception):
    pass


def load_config(path):
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    _validate_config(config)
    return config


def _validate_config(config):
    if "sources" not in config or not config["sources"]:
        raise ConfigError("Config must define at least one entry under 'sources'.")

    for name, source in config["sources"].items():
        if "path" not in source:
            raise ConfigError(f"Source '{name}' is missing a 'path'.")
        if "key" not in source:
            raise ConfigError(f"Source '{name}' is missing a 'key' column.")

    if "reconciliation" in config:
        recon = config["reconciliation"]
        for field in ("primary_source", "secondary_source", "compare_columns"):
            if field not in recon:
                raise ConfigError(f"'reconciliation' section is missing '{field}'.")
        for source_name in (recon["primary_source"], recon["secondary_source"]):
            if source_name not in config["sources"]:
                raise ConfigError(
                    f"Reconciliation references unknown source '{source_name}'."
                )
