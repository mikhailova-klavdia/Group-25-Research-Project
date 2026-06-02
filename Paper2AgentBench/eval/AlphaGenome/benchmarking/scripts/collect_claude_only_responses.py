#!/usr/bin/env python3
"""
Claude-Only Agent Response Collection Script

This script loads a benchmark CSV dataset and runs each query through the Claude CLI
without MCP tools, but encourages Claude to write and execute Python code using the
AlphaGenome library and API to answer questions. It updates the CSV with the agent
responses for further analysis.

IMPORTANT: Before running, be sure to deactivate the AlphaGenome MCP, e.g. as follows:
claude mcp remove alphagenome
Also be sure to run this script from within the alphagenome local repo with access to
the AlphaGenome library and API key.
"""

import os
import sys
import argparse
import subprocess
import json
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("claude_only_response_collection.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def load_benchmark_csv(csv_path: str) -> pd.DataFrame:
    """
    Load the benchmark CSV file and validate its structure.

    Args:
        csv_path: Path to the benchmark CSV file

    Returns:
        pandas DataFrame with the benchmark data
    """
    try:
        df = pd.read_csv(csv_path)
        required_columns = [
            "repo",
            "path",
            "type",
            "question",
            "answer",
            "run_date",
            "agent_response",
            "grade",
            "grade_comments",
        ]

        # Check if all required columns exist
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        logger.info(f"Loaded benchmark CSV with {len(df)} questions")
        return df

    except Exception as e:
        logger.error(f"Error loading CSV file {csv_path}: {e}")
        raise


def create_claude_only_prompt(
    question: str, repo: str, path: str, context: Optional[str] = None
) -> str:
    """
    Create a prompt for Claude CLI that encourages code execution using the AlphaGenome codebase.

    Args:
        question: The question to ask
        repo: Repository URL for context
        path: File path for context
        context: Optional additional context

    Returns:
        Formatted prompt string
    """
    base_prompt = f"""You are an expert in genomics and bioinformatics with access to the AlphaGenome codebase and API.

Repository: {repo}
File: {path}

Question: {question}

IMPORTANT: You must write and execute Python code using the AlphaGenome library to answer this question. Do NOT simply provide answers based on documentation or examples. 
Do NOT provide answers from tutorial notebooks or the executed cells of ipython notebooks. You must:

1. **Write Python code** that uses the AlphaGenome API to solve the specific question
2. **Execute the code** and show the results
3. **Extract the exact answer** from the code execution results
4. **Provide the numerical/quantitative answer** that the question is asking for

Key requirements:
- Use `from alphagenome.data import genome` and `from alphagenome.models import dna_client`
- Load the API key from the .env file using `from dotenv import load_dotenv` and `load_dotenv()`
- Create the DNA model with `dna_model = dna_client.create(os.getenv('ALPHAGENOME_API_KEY'))`
- Write complete, executable code that addresses the specific question
- Show the code execution results and extract the final answer
- If the question asks for a specific value (like quantile_score, nonzero_mean, etc.), provide that exact value

Example approach:
```python
import os
from dotenv import load_dotenv
from alphagenome.data import genome
from alphagenome.models import dna_client

load_dotenv()
dna_model = dna_client.create(os.getenv('ALPHAGENOME_API_KEY'))

# Write code specific to the question here
# Execute the code and show results
# Extract and provide the final answer
```

IMPORTANT: You final response must be a valid JSON object containing exactly two fields:
1. "final_answer": A concise answer containing just the requested value (e.g., a number, gene name, or specific result)
2. "reasoning": Your step-by-step reasoning, the Python code you wrote, execution results, and any calculations you performed

Example response format:
{{
  "final_answer": "GENE_NAME",
  "reasoning": "I wrote Python code to analyze the variant chr1:1234567:A>C for RNA-seq predictions in Colon - Transverse tissue. The code used the AlphaGenome API to score the variant and identified GENE_NAME as having the highest absolute quantile score of 0.987. Here's the code I executed: [code here] and the results: [results here]."
}}

Please ensure your response is valid JSON and the final_answer field contains only the requested value. Do NOT provide any other text or formatting."""

    if context:
        base_prompt = f"Additional Context: {context}\n\n{base_prompt}"

    return base_prompt


def run_claude_cli(
    prompt: str, max_retries: int = 2, timeout: int = 600
) -> tuple[Optional[str], Optional[str], Optional[dict], Optional[float], float]:
    """
    Run the Claude CLI with the given prompt and return (response_text, full_json_response, usage_dict, total_cost_usd, runtime_seconds).
    usage_dict may include keys like input_tokens, output_tokens, total_tokens depending on CLI output.
    total_cost_usd is extracted from the main JSON object, not the usage dict.
    """
    for attempt in range(max_retries):
        start_time = time.time()
        try:
            logger.info(f"Running Claude CLI (attempt {attempt + 1}/{max_retries})")

            # Run Claude CLI with JSON output for usage parsing
            cmd = [
                "claude",
                "--model",
                "claude-sonnet-4-20250514",
                "--allowed-tools",
                "Python",
                "Bash",
                "--add-dir",
                ".",
                "--print",
                "--output-format",
                "json",
                prompt,
            ]
            logger.debug(f"Running command: {' '.join(cmd[:5])} [prompt...]")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, cwd=os.getcwd()
            )
            duration = time.time() - start_time

            if result.returncode == 0:
                stdout_text = result.stdout.strip()
                response_text: Optional[str] = None
                full_json_response: Optional[str] = None
                usage: Optional[dict] = None
                total_cost_usd: Optional[float] = None

                # Try parsing JSON output
                try:
                    parsed = json.loads(stdout_text)
                    full_json_response = stdout_text  # Store the full JSON response
                    obj = parsed[0] if isinstance(parsed, list) and parsed else parsed
                    if isinstance(obj, dict):
                        # Extract response text from "result" field only
                        if isinstance(obj.get("result"), str):
                            response_text = obj["result"]

                        # Extract usage fields if present
                        if isinstance(obj.get("usage"), dict):
                            usage = obj["usage"]
                        else:
                            candidate = {}
                            for k in (
                                "input_tokens",
                                "output_tokens",
                                "total_tokens",
                                "prompt_tokens",
                                "completion_tokens",
                            ):
                                if k in obj:
                                    candidate[k] = obj[k]
                            usage = candidate or None

                        # Extract total_cost_usd from the main object
                        if "total_cost_usd" in obj:
                            try:
                                total_cost_usd = float(obj["total_cost_usd"])
                            except (ValueError, TypeError):
                                total_cost_usd = None
                except Exception:
                    # Fallback: not JSON; use raw stdout as response
                    response_text = stdout_text
                    full_json_response = None
                    usage = None

                if not response_text:
                    response_text = stdout_text

                logger.info("Successfully got response from Claude CLI")
                return response_text, full_json_response, usage, total_cost_usd, duration
            else:
                logger.warning(
                    f"Claude CLI failed with return code {result.returncode}: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(f"Claude CLI timed out after {timeout} seconds (attempt {attempt + 1})")
        except Exception as e:
            duration = time.time() - start_time
            logger.warning(f"Error running Claude CLI (attempt {attempt + 1}): {e}")

        # Wait before retry
        if attempt < max_retries - 1:
            wait_time = 2**attempt
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)

    logger.error("Failed to get response from Claude CLI after all retries")
    return None, None, None, None, 0.0


def process_question(
    row: pd.Series,
    question_index: int,
    total_questions: int,
    timeout: int = 600,
    max_retries: int = 2,
    force_rerun: bool = False,
) -> Dict[str, Any]:
    """
    Process a single question and get the agent response.

    Args:
        row: DataFrame row containing question data
        question_index: Index of the current question (0-based)
        total_questions: Total number of questions
        timeout: Timeout in seconds for Claude CLI calls
        max_retries: Maximum number of retry attempts for Claude CLI calls
        force_rerun: If True, rerun questions that already have responses; if False, skip them

    Returns:
        Dictionary with updated row data
    """
    logger.info(
        f"Processing question {question_index + 1}/{total_questions}: {row['question'][:100]}..."
    )

    # Skip if we already have an agent response (unless force_rerun is True)
    if pd.notna(row["agent_response"]) and row["agent_response"].strip() and not force_rerun:
        logger.info(
            f"Question {question_index + 1} already has agent response, skipping (use --force-rerun to override)"
        )
        return row.to_dict()
    elif pd.notna(row["agent_response"]) and row["agent_response"].strip() and force_rerun:
        logger.info(
            f"Question {question_index + 1} already has agent response, but force_rerun is enabled - will rerun"
        )

    # Create the prompt with codebase context
    prompt = create_claude_only_prompt(question=row["question"], repo=row["repo"], path=row["path"])

    # Get response, full JSON, usage, total_cost_usd, and runtime from Claude CLI
    agent_response, full_json_response, usage, total_cost_usd, runtime_sec = run_claude_cli(
        prompt, max_retries=max_retries, timeout=timeout
    )

    # Update the row data
    updated_row = row.to_dict()
    if agent_response:
        updated_row["agent_response"] = agent_response
        logger.info(f"Successfully collected response for question {question_index + 1}")
    else:
        updated_row["agent_response"] = "ERROR: Failed to get response from Claude CLI"
        logger.error(f"Failed to get response for question {question_index + 1}")

    # Record runtime (seconds)
    updated_row["run_time_seconds"] = round(runtime_sec, 3)

    # Record token usage if available
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("input")
        output_tokens = (
            usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("output")
        )
        cache_creation_input_tokens = usage.get("cache_creation_input_tokens")
        cache_read_input_tokens = usage.get("cache_read_input_tokens")

        # Calculate total tokens as sum of input, output, and cache tokens
        try:
            total_tokens = (
                (int(input_tokens) if input_tokens is not None else 0)
                + (int(output_tokens) if output_tokens is not None else 0)
                + (
                    int(cache_creation_input_tokens)
                    if cache_creation_input_tokens is not None
                    else 0
                )
                + (int(cache_read_input_tokens) if cache_read_input_tokens is not None else 0)
            )
        except Exception:
            total_tokens = None

        if input_tokens is not None:
            try:
                updated_row["tokens_input"] = int(input_tokens)
            except Exception:
                pass
        if output_tokens is not None:
            try:
                updated_row["tokens_output"] = int(output_tokens)
            except Exception:
                pass
        if cache_creation_input_tokens is not None:
            try:
                updated_row["cache_creation_input_tokens"] = int(cache_creation_input_tokens)
            except Exception:
                pass
        if cache_read_input_tokens is not None:
            try:
                updated_row["cache_read_input_tokens"] = int(cache_read_input_tokens)
            except Exception:
                pass
        if total_tokens is not None:
            try:
                updated_row["total_tokens"] = int(total_tokens)
            except Exception:
                pass

        # Extract num_turns from usage
        num_turns = usage.get("num_turns")

        if num_turns is not None:
            try:
                updated_row["num_turns"] = int(num_turns)
            except Exception:
                pass

        # Use total_cost_usd from the function parameter (extracted from main JSON object)
        if total_cost_usd is not None:
            try:
                updated_row["total_cost_usd"] = float(total_cost_usd)
            except Exception:
                pass

    return updated_row


def save_updated_csv(df: pd.DataFrame, output_path: str) -> None:
    """
    Save the updated DataFrame to CSV.

    Args:
        df: Updated DataFrame
        output_path: Path to save the updated CSV
    """
    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Updated CSV saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving updated CSV: {e}")
        raise


def main():
    """Main function to run the Claude-only agent response collection script."""
    parser = argparse.ArgumentParser(
        description="Collect agent responses for benchmark questions using Claude CLI without MCP tools"
    )
    parser.add_argument(
        "input_csv",
        help="Path to the benchmark CSV file (e.g., ag_tutorial_benchmark_2025-09-25.csv)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output CSV file path (default: input file with _with_claude_and_repo_only_responses suffix)",
    )
    parser.add_argument(
        "--start-index",
        "-s",
        type=int,
        default=0,
        help="Index to start processing from (default: 0)",
    )
    parser.add_argument(
        "--end-index",
        "-e",
        type=int,
        help="Index to end processing at (default: process all remaining questions)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum number of retries for Claude CLI calls (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for Claude CLI calls (default: 300)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--force-rerun",
        "-f",
        action="store_true",
        help="Force rerun of questions that already have agent responses (default: skip existing responses)",
    )
    parser.add_argument(
        "--num-runs",
        "-n",
        type=int,
        default=1,
        help="Number of runs to perform for each question (default: 1)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate input file
    if not os.path.exists(args.input_csv):
        logger.error(f"Input CSV file not found: {args.input_csv}")
        sys.exit(1)

    # Set output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input_csv)
        output_path = (
            input_path.parent
            / f"{input_path.stem}_with_claude_and_repo_only_responses{input_path.suffix}"
        )

    try:
        # Load the benchmark CSV
        df = load_benchmark_csv(args.input_csv)

        # Determine processing range
        start_idx = args.start_index
        end_idx = args.end_index if args.end_index is not None else len(df)

        if start_idx < 0 or start_idx >= len(df):
            logger.error(f"Start index {start_idx} is out of range (0-{len(df) - 1})")
            sys.exit(1)

        if end_idx > len(df):
            logger.warning(f"End index {end_idx} exceeds data length {len(df)}, using {len(df)}")
            end_idx = len(df)

        logger.info(
            f"Processing questions {start_idx} to {end_idx - 1} ({end_idx - start_idx} questions) with {args.num_runs} runs each"
        )

        # Initialize list to hold all final rows (preserved + processed runs)
        final_rows = []

        # 1. Add rows before start_idx (preserved as-is, default run_index=1 if missing)
        if start_idx > 0:
            pre_df = df.iloc[:start_idx].copy()
            if "run_index" not in pre_df.columns:
                pre_df["run_index"] = 1
            final_rows.extend(pre_df.to_dict("records"))

        # 2. Process each question in the specified range
        columns_to_clear = [
            "agent_response",
            "run_time_seconds",
            "tokens_input",
            "tokens_output",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "total_tokens",
            "num_turns",
            "total_cost_usd",
        ]

        processed_count = 0
        for i in range(start_idx, end_idx):
            original_row = df.iloc[i]

            for run_number in range(1, args.num_runs + 1):
                # Prepare the row for this run
                current_row = original_row.copy()
                current_row["run_index"] = run_number

                # If this is an additional run (not the first one), clear previous results
                # so process_question treats it as a new pending query
                if run_number > 1:
                    for col in columns_to_clear:
                        if col in current_row:
                            current_row[col] = None

                # Process the question
                # We update the prompt/logging to indicate run number if > 1
                if args.num_runs > 1:
                    logger.info(f"--- Run {run_number}/{args.num_runs} for Question {i + 1} ---")

                updated_row_dict = process_question(
                    current_row, i, len(df), args.timeout, args.max_retries, args.force_rerun
                )
                final_rows.append(updated_row_dict)

            processed_count += 1

            # Save progress every 5 questions execution
            if processed_count % 5 == 0:
                temp_df = pd.DataFrame(final_rows)
                temp_output = f"{output_path}.temp"
                temp_df.to_csv(temp_output, index=False)
                logger.info(f"Progress saved to {temp_output}")

        # 3. Add rows after end_idx (preserved as-is, default run_index=1 if missing)
        if end_idx < len(df):
            post_df = df.iloc[end_idx:].copy()
            if "run_index" not in post_df.columns:
                post_df["run_index"] = 1
            final_rows.extend(post_df.to_dict("records"))

        # Create final DataFrame
        final_df = pd.DataFrame(final_rows)

        # Save the final result
        save_updated_csv(final_df, output_path)

        # Clean up temporary file
        temp_file = f"{output_path}.temp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logger.info("Cleaned up temporary file")

        logger.info(f"Successfully processed {end_idx - start_idx} questions")
        logger.info(f"Results saved to: {output_path}")

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
