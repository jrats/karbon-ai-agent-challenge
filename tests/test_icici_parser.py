import pandas as pd
from custom_parsers.icici_parser import parse
from agent import compare_and_summarize

def test_icici_parser():

    """
    Test that the ICICI PDF parser output matches the ground truth CSV.
    Uses compare_and_summarise function from agent.py.
    """

    expected = pd.read_csv('data/icici/result.csv')
    actual = parse("data/icici/icici sample.pdf")
    # Get mismatch summary
    summary = compare_and_summarize(expected, actual)
    
    if summary != "All rows and columns match exactly.":
        raise AssertionError(summary)