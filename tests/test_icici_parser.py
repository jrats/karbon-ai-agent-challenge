import pandas as pd
from custom_parsers.icici_parser import parse

import pandas as pd

def compare_and_assert(expected: pd.DataFrame, actual: pd.DataFrame):
    """
    Compare two DataFrames and assert equality with diagnostics.
    Handles NaNs, duplicate headers, and index mismatches.
    """

    # Drop any duplicate header rows from actual (e.g., "Date", "Description", etc.) in case of pdfs with multiple pages
    header_row = list(actual.columns)
    actual = actual[~actual.apply(lambda row: list(row) == header_row, axis=1)]

    # Reset index for fair comparison
    expected = expected.reset_index(drop=True)
    actual = actual.reset_index(drop=True)

    # Exact equality check
    if actual.equals(expected):
        return  # Pass silently

    # Otherwise, collect diagnostics
    msg_parts = []

    # Shape mismatch
    if expected.shape != actual.shape:
        msg_parts.append(f"Shape mismatch: expected {expected.shape}, got {actual.shape}")

    # Row match count (NaN handled consistently)
    min_len = min(len(expected), len(actual))
    expected_filled = expected.iloc[:min_len].fillna("")
    actual_filled = actual.iloc[:min_len].fillna("")
    row_matches = (expected_filled.reset_index(drop=True) == actual_filled.reset_index(drop=True)).all(axis=1).sum()
    msg_parts.append(f"{row_matches}/{len(expected)} rows match exactly")

    # Column-level mismatches
    mismatch_summary = {}
    for col in expected.columns:
        if col in actual.columns:
            expected_col = expected[col].reset_index(drop=True).fillna("")
            actual_col = actual[col].reset_index(drop=True).fillna("")
            mismatch_summary[col] = int((expected_col != actual_col).sum())
        else:
            mismatch_summary[col] = "MISSING"
    msg_parts.append("Mismatches by column: " + str(mismatch_summary))

    raise AssertionError("; ".join(msg_parts))



def test_icici_parser():

    """Test that the ICICI PDF parser output matches the ground truth CSV."""

    expected = pd.read_csv('data/icici/result.csv')
    actual = parse("data/icici/icici sample.pdf")
    compare_and_assert(expected, actual)