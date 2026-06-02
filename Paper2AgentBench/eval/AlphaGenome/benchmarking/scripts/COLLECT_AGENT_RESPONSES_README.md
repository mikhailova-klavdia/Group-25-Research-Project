# Agent Response Collection Script

This script loads a benchmark CSV dataset and runs each query through the Claude CLI with the alphagenome-mcp to collect agent responses.

## Prerequisites

1. **Claude CLI installed**: Make sure you have Claude CLI installed and configured
2. **AlphaGenome MCP server**: The alphagenome-mcp server should be running
3. **Environment variables**: API keys should be available in the environment (the script will use the same .env loading as the other scripts)

## Usage

### Basic Usage

```bash
# Process all questions in a benchmark CSV
python collect_agent_responses.py AlphaGenome/benchmarking/data/ag_tutorial_benchmark_2025-09-25.csv

# Specify custom output file
python collect_agent_responses.py ag_tutorial_benchmark_2025-09-25.csv --output results_with_responses.csv

# Process only a subset of questions (useful for resuming)
python collect_agent_responses.py ag_tutorial_benchmark_2025-09-25.csv --start-index 5 --end-index 10

# Enable verbose logging
python collect_agent_responses.py ag_tutorial_benchmark_2025-09-25.csv --verbose

# Run each question 3 independent times (useful for assessing consistency)
python collect_agent_responses.py ag_tutorial_benchmark_2025-09-25.csv --num-runs 3
```

### Command Line Options

- `input_csv`: Path to the benchmark CSV file (required)
- `--output`, `-o`: Output CSV file path (default: input file with `_with_responses` suffix)
- `--start-index`, `-s`: Index to start processing from (default: 0)
- `--end-index`, `-e`: Index to end processing at (default: process all remaining questions)
- `--max-retries`: Maximum number of retries for Claude CLI calls (default: 3)
- `--timeout`: Timeout in seconds for Claude CLI calls (default: 300)
- `--force-rerun`, `-f`: Force rerun of questions that already have agent responses (default: skip existing responses)
- `--num-runs`, `-n`: Number of runs to perform for each question (default: 1)
- `--verbose`, `-v`: Enable verbose logging

## Features

- **Progress tracking**: Saves progress every 5 questions to prevent data loss
- **Resume capability**: Can resume from a specific index if interrupted
- **Error handling**: Robust error handling with retries and logging
- **Skip existing responses**: Automatically skips questions that already have agent responses
- **Logging**: Comprehensive logging to both file and console

## Output

The script creates an updated CSV file with the same structure as the input, but with the `agent_response` column populated with Claude's responses. If `--num-runs` is greater than 1, the output will contain multiple rows for each question, distinguished by the `run_index` column.

## Example Output

```csv
repo,path,type,question,answer,run_date,agent_response,grade,grade_comments
https://github.com/google-genomics-alpha/alphagenome,colab/quick_start.ipynb,tutorial,Create a variant...,APOL4,2025-09-25,"Based on the variant effect prediction analysis, the gene APOL4 shows the most visible expression change...",,
```

## Troubleshooting

1. **Claude CLI not found**: Make sure Claude CLI is installed and in your PATH
2. **MCP server not running**: Ensure the alphagenome-mcp server is running
3. **API key issues**: Check that your AlphaGenome API key is properly configured
4. **Timeout errors**: Increase the timeout value if Claude CLI is taking longer than expected
5. **Unknown option errors**: Make sure you're using the correct Claude CLI version with `--print` support

## Logs

The script creates a log file `agent_response_collection.log` with detailed information about the processing.
