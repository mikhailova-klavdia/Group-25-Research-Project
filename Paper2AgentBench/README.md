# Paper2AgentBench

Benchmarking suite for [Paper2Agent](https://github.com/jmiao24/Paper2Agent), a framework that converts research papers into interactive AI agents.

## Repository Structure

```
Paper2AgentBench/
├── eval/
│   ├── AlphaGenome/              # AlphaGenome agent benchmarking
│   │   ├── benchmarking/         # Benchmark scripts, data, and results
│   │   └── src/                  # AlphaGenome MCP server source
│   ├── 100_compbio_repos/        # 100 computational biology papers evaluation
│   │   ├── 100_papers_link.csv   # Paper links and metadata
│   │   └── 300_questions.csv     # 300 tutorial-derived benchmark questions
│   ├── 26_non_comp_repos/        # 26 non-computational (data/discovery) papers
│   │   └── 100_questions.csv     # 100 synthesis-based benchmark questions
│   ├── 5_nonbio_repos/           # 5 non-biology computational papers
│   │   └── 17_questions.csv      # 17 execution-based benchmark questions
│   └── adversarial_repos/        # Adversarial stress tests
│       ├── AlphaGenome_i{1-4}/   # 4 error-injected AlphaGenome variants
│       ├── POP-TOOLS_i{1-4}/     # 4 error-injected POP-TOOLS variants
│       └── mlearner_i{1-4}/      # 4 error-injected mlearner variants
└── pyproject.toml
```

## Benchmarks

### AlphaGenome Agent
Benchmark queries and scripts for the AlphaGenome agent case study, including tutorial-based, novel, and open-ended queries evaluated against Claude + Repo and Biomni baselines.

### Large-Scale Evaluation
- **100 computational biology papers** — paper links and 300 benchmark questions
- **26 non-computational papers** — 100 synthesis-based benchmark questions
- **5 non-biology papers** — 17 execution-based benchmark questions

### Adversarial Stress Tests
Adversarial repository variants for AlphaGenome, POP-TOOLS, and mlearner, each with 4 categories of injected errors (missing dependencies, broken file paths, typos, deprecated APIs).

## Installation

### Prerequisites
- Python 3.11+
- [Claude Code](https://www.anthropic.com/claude-code)

### Setup
```bash
git clone https://github.com/jmiao24/Paper2AgentBench.git
cd Paper2AgentBench

# Create environment
conda create -n paper2agent python=3.11
conda activate paper2agent

# Install
pip install -e .
```

### Running AlphaGenome Benchmarks

1. Register the MCP server with Claude Code:
```bash
fastmcp install claude-code ./eval/AlphaGenome/src/alphagenome_mcp.py --project ./Paper2AgentBench
```

2. Generate ground truth answers:
```bash
python eval/AlphaGenome/benchmarking/scripts/ag_tutorial_labeler_cli.py
python eval/AlphaGenome/benchmarking/scripts/ag_novel_labeler_cli.py
```

3. Collect agent responses — see READMEs in `eval/AlphaGenome/benchmarking/scripts/` for details on each agent (Paper2Agent MCP, Claude + Repo, Biomni).

4. After manual grading, summarize results:
```bash
python eval/AlphaGenome/benchmarking/scripts/analyze_human_graded_data.py
```

## Citation
```bibtex
@misc{miao2025paper2agent,
      title={Paper2Agent: Reimagining Research Papers As Interactive and Reliable AI Agents},
      author={Jiacheng Miao and Joe R. Davis and Yaohui Zhang and Jonathan K. Pritchard and James Zou},
      year={2025},
      eprint={2509.06917},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2509.06917},
}
```
