
"""
LangGraph-orchestrated agent.
Nodes:
- CodeGen (calls LLM to generate parser)
- Executor (writes parser file)
- Tester (runs pytest, adds diagnostics if fail)
- Fixer (calls LLM to repair parser)

Uses a dataclass AgentState for cleaner state handling.
"""


import os
import sys
import time
import argparse
import subprocess
import pandas as pd
import importlib.util
from dataclasses import dataclass
from openai import OpenAI
from langgraph.graph import StateGraph, END 
from prompts import codegen_template, fixer_template 

client = OpenAI()

## Helper functions ##

def call_llm(prompt: str) -> str:
    """
    Call OpenAI Chat API with a prompt and return generated code.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role':'user', 'content': prompt }],
        temperature=0,
    )
    return response.choices[0].message.content

def write_file(path: str, content: str) -> None:
    """
    Write text content to a file, creating directories if needed.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def run_pytest() -> tuple[bool, str]:
    """
    Run pytest and return (success flag, combined logs).
    """
    try:
        result = subprocess.run(
            ['pytest', '-q'], capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)
    
## Cache utility functions ##

def get_cache_path(bank:str) -> str:
    """Return path for cached successful parser."""
    cache_dir = os.path.join('cache', bank)
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "success.py")

## Agent State ##

@dataclass
class AgentState:
    """
    Container for agent state across graph nodes.
    """

    code: str = ""             # latest generated parser code
    logs: str = ""             # pytest + logs
    success: bool = False      # test result
    attempts: int = 0          # number of times fixes attempted
    bank: str= ""              # bank name 
    pdf_path: str = ""         # path to pdf
    csv_path: str = ""         # path to CSV ground truth
    csv_schema: str = ""       # schema string (column names+ dtypes)
    parser_file: str = ""      # file path to parser

## Comparison ##

def compare_and_summarize(expected: pd.DataFrame, actual: pd.DataFrame) -> str:
    """
    Compare two DataFrames and return human-readable mismatch summary.
    Handles NaN values consistently and drops repeated headers from multi-page PDFs.
    """
    # Drop repeated headers from actual
    header_row = list(actual.columns)
    actual = actual[~actual.apply(lambda row: list(row) == header_row, axis=1)].reset_index(drop=True)

    expected = expected.reset_index(drop=True)

    # Truncate both to min length to avoid shape mismatch in comparison
    min_len = min(len(expected), len(actual))
    expected_filled = expected.iloc[:min_len].fillna("")
    actual_filled = actual.iloc[:min_len].fillna("")

    if expected_filled.equals(actual_filled):
        return "All rows and columns match exactly."

    msg_parts = []
    if expected.shape != actual.shape:
        msg_parts.append(f"Shape mismatch: expected {expected.shape}, got {actual.shape}")

    row_matches = (expected_filled == actual_filled).all(axis=1).sum()
    msg_parts.append(f"{row_matches}/{len(expected)} rows match exactly!")

    mismatch_summary = {}
    for col in expected.columns:
        if col in actual.columns:
            mismatch_summary[col] = int((expected_filled[col] != actual_filled[col]).sum())
        else:
            mismatch_summary[col] = "MISSING"
    msg_parts.append("Mismatches by column: " + str(mismatch_summary))

    return "; ".join(msg_parts)


## Node implementations ##

def codegen(state: AgentState) -> AgentState:
    """
    Generate parser code from LLM using bank-specific prompt.
    """
    #Reuse if successful parser from previous attempts is present.
    success_cache = get_cache_path(state.bank)
    if os.path.exists(success_cache):
        with open(success_cache, "r") as f:
            state.code = f.read()
        print(f"[Cache] Loaded successful parser for {state.bank}")
        state.success = True
        return state
    
    # Else call to the LLM
    prompt = codegen_template.format(
        bank_name=state.bank, pdf_path=state.pdf_path, csv_path=state.csv_path, csv_schema=state.csv_schema
    )
    state.code = call_llm(prompt)
    return state

def executor(state:AgentState) -> AgentState:
    """
    Write generated parser code to file.
    """
    write_file(state.parser_file, state.code)
    return state

def tester(state: AgentState) -> AgentState:
    """
    Run pytest. If failed, re-run parser manually and add diagnostics.
    """

    success, logs = run_pytest()

    if not success:
        try:
            parser_path = state.parser_file
            spec = importlib.util.spec_from_file_location('bank_parser', parser_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules['bank_parser'] = mod
            spec.loader.exec_module(mod)

            actual = mod.parse(state.pdf_path)
            expected = pd.read_csv(state.csv_path)

            # comparison summary between actual and expected
            summary = compare_and_summarize(expected, actual)
            logs += "\n [Agent Diagnostics]" + summary

        except Exception as e:
            logs += f"\n[Agent Diagnostics Error] Could not run manual comparison: {e}"

    state.success = success
    state.logs = logs

    return state

def fixer(state: AgentState) -> AgentState:
    """
    Use LLM to repair parser based on logs and diagnostics.
    """
    prompt = fixer_template.format(
            bank_name=state.bank,
            old_code=state.code,
            error_log=state.logs,
            csv_path=state.csv_path,
            csv_schema=state.csv_schema
            )
    state.code = call_llm(prompt)
    state.attempts += 1
    return state

## Build the graph ##

def build_graph(max_attempts: int=3):
    """
    Build LangGraph with CodeGen → Executor → Tester → Fixer loop.
    """
    graph = StateGraph(AgentState)

    graph.add_node('CodeGen', codegen)
    graph.add_node('Executor', executor)
    graph.add_node('Tester', tester)
    graph.add_node('Fixer', fixer)

    graph.set_entry_point('CodeGen')
    graph.add_edge('CodeGen', 'Executor')
    graph.add_edge('Executor', 'Tester')

    def route_from_tester(state: AgentState):
        if state.success:
            return 'pass'
        elif state.attempts >= max_attempts:
            return 'max_retries'
        else:
            return 'fail'
        
    graph.add_conditional_edges(
        'Tester',
        route_from_tester,
        {'pass': END, 'fail': 'Fixer', 'max_retries': END},
    )

    graph.add_edge('Fixer', 'Executor')
    return graph.compile()

## Utilities ##

def invoke_with_timing(graph, state: AgentState, max_attempts: int = 3) -> AgentState:
    """
    Run the LangGraph workflow with per-attempt timing and row-match updates.
    """
    total_start = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        if state.success:
            break      #codegen produces right output in first attempt

        state.attempts = attempt
        attempt_start = time.perf_counter()
        result_dict = graph.invoke(state)
        state = AgentState(**result_dict)
        elapsed = time.perf_counter() - attempt_start

        #Extracting row match info from logs
        rows_matched = ""
        for line in state.logs.split('\n'):
            if 'rows match exactly' in line:
                rows_matched = line.strip()
                break 
        
        #CLI update per attempt
        status = 'SUCCESS!' if state.success else 'FAILED, moving to next attempt.'
        print(f'Attempt {attempt}: {status} {rows_matched} (Time taken: {elapsed:.2f}s)')

        # Stop early if parser succeeded or proceed till final attempts
        if state.success:
            break

    # Cache the successful parser if any  
    if state.success:
        cache_file = get_cache_path(state.bank)
        write_file(cache_file, state.code)
        print(f"[Cache] Saved successful parser for {state.bank}")
    else:
        print("[Cache] No successful parser; cache not updated.")

    total_elapsed = time.perf_counter() - total_start
    print(f"\nTotal workflow time: {total_elapsed:.2f}s")
    return state 

def infer_csv_schema(csv_path):
    """
    Infer schema string from CSV (colname + dtype).
    """
    df = pd.read_csv(csv_path)
    return ",".join([f"{c} ({df[c].dtype})" for c in df.columns])

## Main Function ##

def main():
    """
    CLI entry: build agent state and run graph.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Bank name (e.g., icici)")
    args = parser.parse_args()

    bank = args.target
    pdf_path = f"data/{bank}/{bank} sample.pdf"
    csv_path = f"data/{bank}/result.csv"
    parser_file = f"custom_parsers/{bank}_parser.py"
    csv_schema = infer_csv_schema(csv_path)

    state = AgentState(
        bank=bank,
        pdf_path=pdf_path,
        csv_path=csv_path,
        csv_schema=csv_schema,
        parser_file=parser_file
    )

    final_graph = build_graph(max_attempts=3)
    final_state = invoke_with_timing(final_graph, state, max_attempts=3)

    print("\n---Workflow Summary---")
    if final_state.success:
        print(f"Parser for {bank} works! Saved at {parser_file}")
    else:
        print("All attempts failed. See logs below:")
        print(final_state.logs)

if __name__ == "__main__":
    main()