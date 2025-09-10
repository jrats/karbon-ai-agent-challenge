import pandas as pd
import pdfplumber
import re
from typing import List, Dict, Any

def parse(pdf_path: str) -> pd.DataFrame:
    transactions = []
    headers_seen = set()

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if is_header_row(row) and tuple(row) in headers_seen:
                            continue
                        headers_seen.add(tuple(row))
                        transaction = parse_table_row(row)
                        if transaction:
                            transactions.append(transaction)
            else:
                text = page.extract_text()
                if text:
                    for line in text.split('\n'):
                        transaction = parse_text_line(line)
                        if transaction:
                            transactions.append(transaction)

    df = pd.DataFrame(transactions)
    df = clean_dataframe(df)
    return df

def is_header_row(row: List[str]) -> bool:
    return all(re.match(r'^\s*Date\s*$', cell) or re.match(r'^\s*Description\s*$', cell) or 
               re.match(r'^\s*Debit Amt\s*$', cell) or re.match(r'^\s*Credit Amt\s*$', cell) or 
               re.match(r'^\s*Balance\s*$', cell) for cell in row)

def parse_table_row(row: List[str]) -> Dict[str, Any]:
    if len(row) < 5:
        return None
    return {
        'Date': row[0].strip(),
        'Description': row[1].strip(),
        'Debit Amt': parse_amount(row[2].strip()) if row[2].strip() not in ['Debit Amt', ''] else None,
        'Credit Amt': parse_amount(row[3].strip()) if row[3].strip() not in ['Credit Amt', ''] else None,
        'Balance': parse_amount(row[4].strip()) if row[4].strip() not in ['Balance', ''] else None
    }

def parse_text_line(line: str) -> Dict[str, Any]:
    parts = line.split()
    if len(parts) < 5:
        return None
    return {
        'Date': parts[0],
        'Description': ' '.join(parts[1:-3]),
        'Debit Amt': parse_amount(parts[-3]),
        'Credit Amt': parse_amount(parts[-2]),
        'Balance': parse_amount(parts[-1])
    }

def parse_amount(amount_str: str) -> float:
    if amount_str == '':
        return float('nan')
    return float(amount_str.replace(',', '').replace('₹', '').strip())

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = ['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')
    df['Debit Amt'] = pd.to_numeric(df['Debit Amt'], errors='coerce')
    df['Credit Amt'] = pd.to_numeric(df['Credit Amt'], errors='coerce')
    df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce')
    return df[['Date', 'Description', 'Debit Amt', 'Credit Amt', 'Balance']]