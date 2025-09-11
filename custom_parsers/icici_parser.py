import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any

def parse(pdf_path: str) -> pd.DataFrame:
    """
    Parse the ICICI bank statement PDF and return a DataFrame with transaction details.

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
                        if row == headers or not any(row):  # Skip header and empty rows
                            continue
                        transactions.append(parse_row(row))
            else:
                # Fallback to text extraction
                text = page.extract_text()
                if text:
                    for line in text.split('\n'):
                        row = parse_line(line)
                        if row:
                            transactions.append(row)

    # Create DataFrame and remove duplicate headers
    df = pd.DataFrame(transactions, columns=headers)
    df = df[~df['Date'].isin(headers)]  # Remove repeated headers
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce').dt.strftime('%d-%m-%Y')
    df['Debit Amt'] = pd.to_numeric(df['Debit Amt'].replace('', pd.NA), errors='coerce')
    df['Credit Amt'] = pd.to_numeric(df['Credit Amt'].replace('', pd.NA), errors='coerce')
    df['Balance'] = pd.to_numeric(df['Balance'].replace('', pd.NA), errors='coerce')

    return df

def parse_row(row: List[str]) -> Dict[str, Any]:
    """
    Parse a row from the table into a dictionary.

    Args:
        row (List[str]): A list representing a row from the table.

    Returns:
        Dict[str, Any]: A dictionary with parsed transaction details.
    """
    date = row[0]
    description = row[1]
    debit = row[2] if len(row) > 2 else ''
    credit = row[3] if len(row) > 3 else ''
    balance = row[4] if len(row) > 4 else ''
    
    return {
        "Date": date,
        "Description": description,
        "Debit Amt": debit,
        "Credit Amt": credit,
        "Balance": balance
    }

def parse_line(line: str) -> Dict[str, Any]:
    """
    Parse a line of text into a dictionary.

    Args:
        line (str): A line of text from the PDF.

    Returns:
        Dict[str, Any]: A dictionary with parsed transaction details or empty if not valid.
    """
    # Example regex pattern, adjust according to actual line format
    pattern = r'(\d{2}-\d{2}-\d{4})\s+(.+?)\s+([\d,]*\.?\d*)?\s+([\d,]*\.?\d*)?\s+([\d,]*\.?\d*)?'
    match = re.match(pattern, line)
    if match:
        return {
            "Date": match.group(1),
            "Description": match.group(2),
            "Debit Amt": match.group(3) if match.group(3) else '',
            "Credit Amt": match.group(4) if match.group(4) else '',
            "Balance": match.group(5) if match.group(5) else ''
        }
    return {}  # Return empty dict if line does not match the expected format