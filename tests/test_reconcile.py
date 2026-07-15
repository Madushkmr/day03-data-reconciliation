"""
Unit tests for pipeline.reconcile — checks matched/mismatched/missing
classification using small synthetic DataFrames.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.reconcile import reconcile


def test_all_matched_when_amounts_agree():
    primary = pd.DataFrame({"order_id": [1, 2, 3], "amount": [10.0, 20.0, 30.0]})
    secondary = pd.DataFrame({"order_id": [1, 2, 3], "amount": [10.0, 20.0, 30.0]})
    result = reconcile(primary, secondary, "order_id", "order_id", ["amount"])
    assert sorted(result["matched"]) == [1, 2, 3]
    assert result["mismatched"] == []
    assert result["missing_in_secondary"] == []
    assert result["missing_in_primary"] == []


def test_missing_rows_detected_both_directions():
    primary = pd.DataFrame({"order_id": [1, 2], "amount": [10.0, 20.0]})
    secondary = pd.DataFrame({"order_id": [2, 3], "amount": [20.0, 30.0]})
    result = reconcile(primary, secondary, "order_id", "order_id", ["amount"])
    assert result["missing_in_secondary"] == [1]
    assert result["missing_in_primary"] == [3]
    assert result["matched"] == [2]


def test_mismatch_beyond_tolerance():
    primary = pd.DataFrame({"order_id": [1], "amount": [100.0]})
    secondary = pd.DataFrame({"order_id": [1], "amount": [105.0]})
    result = reconcile(primary, secondary, "order_id", "order_id", ["amount"], tolerance=1.0)
    assert result["matched"] == []
    assert len(result["mismatched"]) == 1
    assert result["mismatched"][0]["key"] == 1
    assert result["mismatched"][0]["diffs"]["amount"] == {"primary": 100.0, "secondary": 105.0}


def test_mismatch_within_tolerance_counts_as_matched():
    primary = pd.DataFrame({"order_id": [1], "amount": [100.00]})
    secondary = pd.DataFrame({"order_id": [1], "amount": [100.005]})
    result = reconcile(primary, secondary, "order_id", "order_id", ["amount"], tolerance=0.01)
    assert result["matched"] == [1]
    assert result["mismatched"] == []


def test_duplicate_key_in_primary_does_not_crash():
    # A duplicated key is a data-quality issue that validate.py catches
    # separately; reconcile() should still run without error, comparing
    # against the first occurrence of the duplicated key.
    primary = pd.DataFrame({"order_id": [1, 1, 2], "amount": [10.0, 10.0, 20.0]})
    secondary = pd.DataFrame({"order_id": [1, 2], "amount": [10.0, 20.0]})
    result = reconcile(primary, secondary, "order_id", "order_id", ["amount"])
    assert sorted(result["matched"]) == [1, 2]
    assert result["mismatched"] == []
