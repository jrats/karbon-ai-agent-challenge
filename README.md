# Bank Statement Parser Agent

This project implements a LangGraph-orchestrated agent that generates, tests, and fixes Python parsers for bank statements using LLMs. The agent loops through CodeGen → Executor → Tester → Fixer nodes until a parser passes all tests. It uses pdfplumber for PDF extraction, pandas for tabular processing, and caches successful parsers for reuse.
__________________________________________________________________________________

# 5-Step Run Instructions

1.Set up environment

Install dependencies:

pip install -r requirements.txt


Set your OpenAI API key:

export OPENAI_API_KEY=your_api_key_here


Add project root to PYTHONPATH (⚠️ important for imports):

 macOS / Linux
export PYTHONPATH=$(pwd)
Windows (PowerShell)
setx PYTHONPATH "%cd%"


2.Prepare data
Place the bank PDF and corresponding CSV in data/<bank>/, e.g.:

data/icici/icici sample.pdf
data/icici/result.csv


3.Run the agent

python agent.py --target icici


4.Check workflow output

Parser results and logs appear in the console per attempt.

On success, parser saved to custom_parsers/<bank>_parser.py.

Successful parser cached in cache/<bank>/success.py.

5.Test parser manually

pytest -q test/test_icici_parser.py

________________________________________________________________________________

# Agent Diagram

The agent consists of four main nodes orchestrated via LangGraph:

CodeGen: Generates parser code using the LLM based on the bank PDF and expected CSV schema.

Executor: Writes the generated parser code to a Python file.

Tester: Runs automated tests using pytest and compares parser output against the ground truth CSV, adding diagnostics for failures.

Fixer: Calls the LLM to repair the parser based on test logs and mismatches.

The workflow loops from Tester → Fixer → Executor until either the parser succeeds or the maximum number of attempts is reached. Successful parsers are cached for future reuse, reducing redundant LLM calls.



