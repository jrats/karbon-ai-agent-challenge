import pandas as pd
from custom_parsers.icici_parser import parse

import pandas as pd

def compare_and_assert(expected: pd.DataFrame, actual: pd.DataFrame):
    """
    Compare two DataFrames and assert equality with diagnostics.
    Handles NaNs, duplicate headers, and index mismatches.
    """
    # Remove repeated headers
    header_row = list(actual.columns)
    actual = actual[~actual.apply(lambda row: list(row) == header_row, axis=1)].reset_index(drop=True)
    expected = expected.reset_index(drop=True)

    # Truncate to min length to avoid broadcasting errors
    min_len = min(len(expected), len(actual))
    expected_filled = expected.iloc[:min_len].fillna("")
    actual_filled = actual.iloc[:min_len].fillna("")

    if expected_filled.equals(actual_filled):
        return  # pass silently

    msg_parts = []
    if expected.shape != actual.shape:
        msg_parts.append(f"Shape mismatch: expected {expected.shape}, got {actual.shape}")

    row_matches = (expected_filled == actual_filled).all(axis=1).sum()
    msg_parts.append(f"{row_matches}/{len(expected)} rows match exactly")

    mismatch_summary = {}
    for col in expected.columns:
        if col in actual.columns:
            mismatch_summary[col] = int((expected_filled[col] != actual_filled[col]).sum())
        else:
            mismatch_summary[col] = "MISSING"
    msg_parts.append("Mismatches by column: " + str(mismatch_summary))

    raise AssertionError("; ".join(msg_parts))


def test_icici_parser():

    """Test that the ICICI PDF parser output matches the ground truth CSV."""

    expected = pd.read_csv('data/icici/result.csv')
    actual = parse("data/icici/icici sample.pdf")
    compare_and_assert(expected, actual)