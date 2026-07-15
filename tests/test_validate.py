"""
Unit tests for pipeline.validate — checks each rule type in isolation
using small synthetic DataFrames, independent of the sample CSVs.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.validate import validate_source


def test_required_columns_missing():
    df = pd.DataFrame({"order_id": [1, 2]})
    rules = {"required_columns": ["order_id", "amount"]}
    issues = validate_source("test", df, rules)
    assert len(issues) == 1
    assert issues[0]["rule"] == "required_columns"
    assert issues[0]["column"] == "amount"


def test_not_null_detects_nulls():
    df = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": ["A", None, "C"]})
    rules = {"not_null": ["customer_id"]}
    issues = validate_source("test", df, rules, key_column="order_id")
    assert len(issues) == 1
    assert issues[0]["rule"] == "not_null"
    assert issues[0]["row_key"] == 2


def test_unique_detects_duplicates():
    df = pd.DataFrame({"order_id": [1, 2, 2, 3]})
    rules = {"unique": ["order_id"]}
    issues = validate_source("test", df, rules, key_column="order_id")
    assert len(issues) == 2  # both rows with the duplicated value are flagged
    assert all(issue["rule"] == "unique" for issue in issues)


def test_numeric_range_flags_out_of_bounds():
    df = pd.DataFrame({"order_id": [1, 2, 3], "amount": [50.0, 150.0, -10.0]})
    rules = {"numeric_range": {"amount": {"min": 0, "max": 100}}}
    issues = validate_source("test", df, rules, key_column="order_id")
    assert len(issues) == 2  # 150.0 and -10.0 are out of range


def test_clean_data_has_no_issues():
    df = pd.DataFrame({
        "order_id": [1, 2, 3],
        "customer_id": ["A", "B", "C"],
        "amount": [10.0, 20.0, 30.0],
    })
    rules = {
        "required_columns": ["order_id", "customer_id", "amount"],
        "not_null": ["customer_id"],
        "unique": ["order_id"],
        "numeric_range": {"amount": {"min": 0, "max": 100}},
    }
    issues = validate_source("test", df, rules, key_column="order_id")
    assert issues == []
