# Biomni Agent Response Collection Script

This script loads a benchmark CSV dataset and runs each query through the Biomni A1 agent to collect agent responses. It updates the CSV with the agent responses for further analysis.

## Key Features

- **Biomni A1 Agent Integration**: Uses the Biomni A1 agent for response generation
- **Consistent Output Format**: Produces the same output fields as other collection scripts
- **Command Line Interface**: Full CLI with progress tracking and error handling
- **Flexible Configuration**: Configurable data path, LLM model, and processing options

## Prerequisites

1. **Biomni Package**: Install the Biomni package with A1 agent support
2. **Data Directory**: Ensure Biomni data directory exists (~11GB download on first run)
3. **AlphaGenome API Key**: Must have ALPHAGENOME_API_KEY in .env file
4. **Python Dependencies**: pandas, pathlib, logging

## Usage

### Basic Usage

Prior to any use, be sure you are in the Biomni local repo and have started the environment like so:
```bash
cd ~/projects/Biomni
conda activate biomni_e1
```
This steps assume you have downloaded the Biomni repo locally and built the environment. If you have not, you can 
follow these steps [here](https://github.com/snap-stanford/Biomni/)


```bash
# Process all questions in a benchmark CSV
python collect_biomni_responses.py AlphaGenome/benchmarking/data/ag_tutorial_benchmark_2025-09-25.csv

# Specify custom output file
python collect_biomni_responses.py ag_tutorial_benchmark_2025-09-25.csv --output biomni_results.csv

# Process only a subset of questions
python collect_biomni_responses.py ag_tutorial_benchmark_2025-09-25.csv --start-index 5 --end-index 10

# Enable verbose logging
python collect_biomni_responses.py ag_tutorial_benchmark_2025-09-25.csv --verbose

# Run each question 3 independent times
python collect_biomni_responses.py ag_tutorial_benchmark_2025-09-25.csv --num-runs 3
```

### Command Line Options

- `input_csv`: Path to the benchmark CSV file (required)
- `--output`, `-o`: Output CSV file path (default: input file with `_with_biomni_responses` suffix)
- `--start-index`, `-s`: Index to start processing from (default: 0)
- `--end-index`, `-e`: Index to end processing at (default: process all remaining questions)
- `--max-retries`: Maximum number of retries for agent calls (default: 2)
- `--timeout`: Timeout in seconds for agent calls (default: 600)
- `--data-path`: Path to Biomni data directory (default: ~/projects/Biomni/data)
- `--llm`: LLM model to use (default: claude-sonnet-4-20250514)
- `--force-rerun`, `-f`: Force rerun of questions that already have agent responses
- `--num-runs`, `-n`: Number of runs to perform for each question (default: 1)
- `--verbose`, `-v`: Enable verbose logging

### Advanced Usage

```bash
# Use custom data path and LLM model
python collect_biomni_responses.py benchmark.csv --data-path /custom/path --llm claude-haiku-3

# Process with custom timeout and retry settings
python collect_biomni_responses.py benchmark.csv --timeout 1200 --max-retries 3

# Resume processing from a specific index
python collect_biomni_responses.py benchmark.csv --start-index 50
```

## Output Format

The script produces CSV files with the following additional columns (if `--num-runs` > 1, a `run_index` column is also added):

- `agent_response`: Final results text from Biomni agent
- `full_agent_response_json`: Full response text from Biomni agent
- `run_time_seconds`: Runtime in seconds for each question
- `tokens_input`: Input tokens (None for Biomni)
- `tokens_output`: Output tokens (None for Biomni)
- `cache_creation_input_tokens`: Cache creation tokens (None for Biomni)
- `cache_read_input_tokens`: Cache read tokens (None for Biomni)
- `total_tokens`: Total tokens (None for Biomni)
- `num_turns`: Number of turns (None for Biomni)
- `total_cost_usd`: Total cost in USD (None for Biomni)

## Biomni Agent Response Format

The Biomni A1 agent returns responses as tuples:
- **First element**: Full response text (stored in `full_agent_response_json`)
- **Second element**: Final results text (stored in `agent_response`)

## Notes

- Biomni does not provide token usage or cost information, so these fields are set to None
- The script includes progress tracking and saves temporary files every 5 questions
- Error handling includes retry logic with exponential backoff
- The script skips questions that already have agent responses

## Example Output

```csv
repo,path,type,question,answer,run_date,agent_response,grade,grade_comments,full_agent_response_json,run_time_seconds,tokens_input,tokens_output,cache_creation_input_tokens,cache_read_input_tokens,total_tokens,num_turns,total_cost_usd
https://github.com/...,example.py,tutorial,What is the nonzero_mean value?,42.5,2025-01-01,42.5,1.0,Correct,Full response text here...,15.234,None,None,None,None,None,None,None
```
