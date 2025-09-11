import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any

def parse(pdf_path: str) -> pd.DataFrame:
    """
    Parse the ICICI bank statement PDF and return a DataFrame with the transaction details.

    Args:
        pdf_path (str): The path to the PDF file to be parsed.

    Returns:
        pd.DataFrame: A DataFrame containing the parsed transaction data.
    """
    transactions = []
    headers = ["Date", "Description", "Debit Amt", "Credit Amt", "Balance"]

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Try to extract tables first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if row and any(row):  # Check if the row is not empty
                            transactions.append(row)
            else:
                # Fallback to text extraction if no tables are found
                text = page.extract_text()
                if text:
                    lines = text.split('\n')
                    for line in lines:
                        # Use regex to match the expected transaction format
                        match = re.match(r'(\d{2}-\d{2}-\d{4})\s+(.*?)\s+([\d,]*\.?\d*)?\s+([\d,]*\.?\d*)?\s+([\d,]*\.?\d*)?', line)
                        if match:
                            transactions.append(list(match.groups()))

    # Create DataFrame and clean up
    df = pd.DataFrame(transactions, columns=headers)

    # Remove repeated header rows
    df = df[~df['Date'].str.contains('Date', na=False)]

    # Normalize date format to dd-mm-yyyy
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce').dt.strftime('%d-%m-%Y')

    # Convert amounts to floats, preserving NaN for missing values
    df['Debit Amt'] = pd.to_numeric(df['Debit Amt'].str.replace(',', ''), errors='coerce')
    df['Credit Amt'] = pd.to_numeric(df['Credit Amt'].str.replace(',', ''), errors='coerce')
    df['Balance'] = pd.to_numeric(df['Balance'].str.replace(',', ''), errors='coerce')

    # Ensure correct column order
    df = df[headers]

    return df