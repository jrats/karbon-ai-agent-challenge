""" 
Prompt templates for the LLM. These are filled at runtime to be sent to the LLM. 
The LLM is expected to return Python source code for the parser using the codegen_template 
and corrected Python source code when using the fixer_template.
"""

from langchain.prompts import PromptTemplate

# Code generation prompt
codegen_template = PromptTemplate(
    input_variables=["bank_name", "pdf_path", "csv_path", "csv_schema"],
    template="""
    You are an expert Python developer.
    Your task is to create a bank statement parser for the bank: {bank_name}.

    The input is a PDF file located at: {pdf_path}
    The expected output schema is defined by the CSV at: {csv_path}

    **Requirements:**
    - Create a Python module at 'custom_parsers/{bank_name}_parser.py'.
    - Implement the function:
        def parse(pdf_path: str) -> pd.DataFrame
    - Use the 'pdfplumber' library to extract both **tables and text** from the PDF.
    - Iterate over **every page** in the PDF:
      - Prefer extracting tables when available.
      - If no valid table is found, fall back to line-based text extraction and parse transactions manually.
    - Combine results from all pages into a single pandas DataFrame.
    - **Remove repeated header rows** if they appear on multiple pages.
    - Normalize **all dates to dd-mm-yyyy format** (Indian bank statements standard).
    - Preserve missing values (NaN) exactly as in the CSV — do not replace empty debit/credit cells with 0.0.
    - Convert amounts to floats where values exist, handle negatives correctly.
    - Ensure correct column order and datatypes.
    - Add type hints and docstrings. Follow PEP8 style and write modular code.

    **Output format:**
    - Return only the full Python code for the parser file.
    - Do not include explanations or markdown.
    """
)


# Code correction prompt
fixer_template = PromptTemplate(
    input_variables=["bank_name", "old_code", "error_log", "csv_path", "csv_schema"],
    template="""
    You are an expert Python developer.
    The parser for the bank: {bank_name} failed tests.

    Here is the current code:
    {old_code}

    Here is the test failure message (includes row match counts and per-column mismatches):
    {error_log}

    The expected schema is defined by the CSV at: {csv_path}

    **Requirements:**
    - Continue to use 'pdfplumber' to extract both **tables and text** from the PDF.
    - Iterate over **every page** in the PDF:
      - Prefer extracting tables when available.
      - If no valid table is found, fall back to line-based text extraction and parse transactions manually.
    - Combine results from all pages into a single pandas DataFrame.
    - **Remove repeated header rows** if they appear on subsequent pages.
    - Normalize **all dates to dd-mm-yyyy format** (Indian bank statements standard).
    - Preserve missing values (NaN) exactly as in the CSV — do not replace empty debit/credit cells with 0.0.
    - Use the mismatch details (row match count, per-column mismatches) to target fixes precisely.
    - Adjust the extraction/cleaning logic so the DataFrame matches the schema exactly: {csv_schema}.
    - Convert amounts to floats where values exist, handle negatives correctly.
    - Preserve working parts of the code — make minimal necessary fixes.
    - Include type hints, docstrings, and maintain clean, modular code.

    **Output format:**
    - Return only the corrected full Python code for the parser file.
    - Do not include explanations or markdown.
    """
)
