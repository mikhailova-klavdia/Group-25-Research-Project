# Claude-Only Agent Response Collection Script

This script loads a benchmark CSV dataset and runs each query through the Claude CLI without MCP tools, but encourages Claude to write and execute Python code using the AlphaGenome library and API to answer questions.

## Key Differences from MCP Version

- **No MCP Tools**: Uses Claude CLI without MCP server integration
- **Code Execution**: Encourages Claude to write and execute Python code using AlphaGenome library
- **Direct API Usage**: Claude uses the AlphaGenome API directly through Python code
- **Different Output Format**: Creates files with `_with_claude_only_responses` suffix

## Prerequisites

1. **Claude CLI installed**: Make sure you have Claude CLI installed and configured
2. **No MCP server required**: This version doesn't need the alphagenome-mcp server running
3. **Claude API access**: Requires valid Claude API credentials
4. **AlphaGenome library**: Must have access to AlphaGenome Python library and API key
5. **MCP deactivated**: Run `claude mcp remove alphagenome` before using this script

## Usage

### Basic Usage

```bash
# Process all questions in a benchmark CSV
python collect_claude_only_responses.py AlphaGenome/benchmarking/data/ag_tutorial_benchmark_2025-09-25.csv

# Specify custom output file
python collect_claude_only_responses.py ag_tutorial_benchmark_2025-09-25.csv --output claude_only_results.csv

# Process only a subset of questions
python collect_claude_only_responses.py ag_tutorial_benchmark_2025-09-25.csv --start-index 5 --end-index 10

# Enable verbose logging
python collect_claude_only_responses.py ag_tutorial_benchmark_2025-09-25.csv --verbose

# Run each question 3 independent times
python collect_claude_only_responses.py ag_tutorial_benchmark_2025-09-25.csv --num-runs 3
```

### Command Line Options

- `input_csv`: Path to the benchmark CSV file (required)
- `--output`, `-o`: Output CSV file path (default: input file with `_with_claude_only_responses` suffix)
- `--start-index`, `-s`: Index to start processing from (default: 0)
- `--end-index`, `-e`: Index to end processing at (default: process all remaining questions)
- `--max-retries`: Maximum number of retries for Claude CLI calls (default: 3)
- `--timeout`: Timeout in seconds for Claude CLI calls (default: 300)
- `--force-rerun`, `-f`: Force rerun of questions that already have agent responses
- `--num-runs`, `-n`: Number of runs to perform for each question (default: 1)
- `--verbose`, `-v`: Enable verbose logging

## Prompting Strategy

The script uses a code execution prompting approach that:

1. **Requires code execution**: Claude must write and execute Python code using AlphaGenome library
2. **Direct API usage**: Encourages direct use of AlphaGenome API through Python code
3. **Specific imports**: Provides exact import statements and setup code
4. **Result extraction**: Requires showing execution results and extracting final answers
5. **No documentation copying**: Explicitly forbids copying values from tutorials/documentation

## Output

The script creates an updated CSV file with the same structure as the input, but with the `agent_response` column populated with Claude's responses based on code execution using the AlphaGenome library. If `--num-runs` is greater than 1, the output will contain multiple rows for each question, distinguished by the `run_index` column.

## Example Output

```csv
repo,path,type,question,answer,run_date,agent_response,grade,grade_comments
https://github.com/google-genomics-alpha/alphagenome,colab/quick_start.ipynb,tutorial,Create a variant...,APOL4,2025-09-25,"I'll write Python code to analyze this variant effect prediction:

```python
import os
from dotenv import load_dotenv
from alphagenome.data import genome
from alphagenome.models import dna_client

load_dotenv()
dna_model = dna_client.create(os.getenv('ALPHAGENOME_API_KEY'))

variant = genome.Variant(
    chromosome='chr22',
    position=36201698,
    reference_bases='A',
    alternate_bases='C',
)
interval = variant.reference_interval.resize(dna_client.SEQUENCE_LENGTH_1MB)
variant_scorer = variant_scorers.RECOMMENDED_VARIANT_SCORERS['RNA_SEQ']
variant_scores = dna_model.score_variant(
    interval=interval, variant=variant, variant_scorers=[variant_scorer]
)
q1_scores = variant_scorers.tidy_scores([variant_scores], match_gene_strand=True)
q1_answer = q1_scores[q1_scores['ontology_curie'] == 'UBERON:0001157']
q1_answer = q1_answer.loc[q1_answer['quantile_score'].abs().idxmax()]
print(f'Gene with strongest expression change: {q1_answer.gene_name}')
```

Result: APOL4",,
```

## Troubleshooting

1. **Claude CLI not found**: Make sure Claude CLI is installed and in your PATH
2. **API key issues**: Check that your Claude API credentials are properly configured
3. **Timeout errors**: Increase the timeout value if Claude CLI is taking longer than expected
4. **Unknown option errors**: Make sure you're using the correct Claude CLI version with `--print` support

## Logs

The script creates a log file `claude_only_response_collection.log` with detailed information about the processing.
