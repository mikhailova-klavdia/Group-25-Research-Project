# Evaluation Strategy

This document defines how to evaluate the project against the four research questions in [README.md](../README.md) and [explanation.md](../explanation.md). It is a strategy document, not a results report.

## Scope

The evaluation should cover both agent paths in this repository:

- The structured single-agent CLI in `research_agents.main`
- The ReAct path in `research_agents.react_main`

It should also support comparison against external agentic coding baselines when those systems can be run on the same paper and question sets.

## Evaluation Matrix

| Research question | Primary task | Main datasets | Primary metrics |
|---|---|---|---|
| RQ1. Paper + repo question answering | Answer predefined benchmark questions from a paper and its repository | Paper2AgentBench questions, local paper/repo workspaces, human ground truth where available | Answer accuracy, exact match, partial credit, answerability rate |
| RQ2. Enzyme reasoning-chain diagnosis | Detect the wrong step in an expert chain and explain why it fails | Enzyme chain set in `evaluation/human evaluation/iteration_1/Chains/` plus annotations | Step-detection accuracy, rubric score, LLM-as-judge score, inter-annotator agreement |
| RQ3. Reproduction under missing vs insufficient information | Reproduce experiments, then measure degradation under controlled information gaps | Base paper/repo tasks plus two ablated variants per task | Accuracy drop, success rate drop, blocked-run rate, error-type shift |
| RQ4. Single-agent vs multi-agent vs SOTA systems | Compare architectures on reproduction tasks | Same reproduction question set across all systems | Accuracy, total tokens, estimated API cost, runtime |

## Common Experimental Principles

- Use the same paper PDF and repository snapshot for every compared system.
- Run each question in a fresh workspace, but keep the existing per-paper shared `.venv/` policy when using this repository.
- Keep prompts, turn limits, timeout limits, and model choice fixed within a single comparison unless the variable under study is the prompt, limit, or model itself.
- Separate infeasible tasks from incorrect answers. A blocked run is not the same as a wrong answer.
- Save every raw artifact needed for audit: chain JSON, final answer, token usage, runtime, cost estimate, and evaluator annotations.

## RQ1: Paper and Repository Question Answering

### Goal

Measure how often the agent answers predefined questions correctly when grounded in both the scientific paper and the associated repository.

### Dataset

- Use the question sets already present in `question-answers/` for the current bio papers.
- Extend with Paper2AgentBench questions for any additional locally available papers under `papers/<slug>/`.
- For questions with explicit ground truth, use automatic grading first.
- For questions without explicit ground truth, use human annotation with a fixed rubric.

### Protocol

1. Run each question with the structured single-agent path.
2. Run the same question with the ReAct path.
3. Keep the same model for both runs in the main comparison.
4. Store outputs under `evaluation/eval_runs/<date>-<owner>-<model>-<variant>/`.

### Metrics

- Exact-match accuracy for deterministic numeric or categorical answers
- Numeric-tolerance accuracy for floating-point answers
- Partial-credit score for open text answers
- Answerability rate: fraction of questions that the agent can answer with repository or paper evidence
- Blocked rate: fraction of questions stopped by missing files, missing weights, or environment issues

### Reporting

Report per-paper and aggregate results, then break errors into:

- wrong reasoning
- wrong execution
- hallucinated answer
- blocked by missing dependency
- blocked by missing input
- insufficient evidence in source material

## RQ2: Enzyme Reasoning-Chain Diagnosis

### Goal

Measure whether the agent can identify the incorrect step in an expert-constructed enzyme reasoning chain and justify the failure consistently.

### Dataset

- Use the enzyme chain JSON files under `evaluation/human evaluation/iteration_1/Chains/`.
- Use existing human annotation files in `evaluation/human evaluation/iteration_1/ann_1/` and any later annotator folders as ground-truth and agreement references.

### Protocol

1. Present one chain at a time to the evaluator agent.
2. Require the evaluator to return:
   - the first incorrect step
   - a short failure explanation
   - an overall confidence or uncertainty note
3. Score the output against the benchmark annotation.
4. Run human review on a subset or all outputs using the same rubric.
5. Run an LLM-as-judge pass using a fixed judging prompt for consistency checks.

### Metrics

- Step-detection accuracy: whether the predicted incorrect step matches the annotated step
- Distance-to-true-step: absolute difference when the exact step is missed
- Human rubric score for explanation quality
- Internal-consistency score from the judge model
- Cohen's kappa or equivalent agreement between human annotators and the judge where applicable

### Reporting

Separate step-localization from explanation quality. A model can find the right step for the wrong reason, or miss the step but still give a plausible explanation. Those should not be collapsed into one score.

## RQ3: Reproduction Under Information Gaps

### Goal

Measure how robust experiment reproduction is when critical information is intentionally degraded in two different ways.

### Conditions

- Full-information condition: original paper, repository, and local benchmark assets
- Missing condition: remove one or more parameters, files, or setup details required for reproduction
- Insufficient condition: leave relevant information present but incomplete, ambiguous, or too weak to derive the answer safely

### Constructing the Ablations

For each reproduction task, define one `missing` and one `insufficient` variant.

Examples of `missing`:

- remove a required checkpoint path
- remove a key CLI argument from the question
- hide one required config file

Examples of `insufficient`:

- keep the script name but omit the parameter value needed to run it
- keep an evaluation description but remove the threshold or split definition
- keep repository references that indicate where to look, but not enough detail to compute the answer exactly

### Protocol

1. Run each task in the full-information condition.
2. Re-run the same task in the `missing` condition.
3. Re-run the same task in the `insufficient` condition.
4. Keep everything else fixed: model, architecture, runtime limits, and workspace rules.

### Metrics

- Accuracy in each condition
- Absolute and relative performance degradation from full-information to `missing`
- Absolute and relative performance degradation from full-information to `insufficient`
- Success-to-blocked transition rate
- Error-type distribution shift across the three conditions

### Reporting

The key result is not just lower accuracy. Show whether degradation is caused by:

- brittle dependency handling
- inability to recognize missing evidence
- hallucinated gap-filling
- failure to distinguish impossible from uncertain

## RQ4: Single-Agent and Multi-Agent Comparison Against SOTA

### Goal

Compare this repository's single-agent and multi-agent variants against strong external agentic coding baselines on reproduction tasks.

### Systems to Compare

- Structured single-agent path in this repository
- ReAct worker-only path if retained
- ReAct worker-plus-critic path
- External state-of-the-art coding agents that can be run on the same local tasks

### Fairness Controls

- Same question set
- Same repository snapshot and paper version
- Same machine class if possible
- Same timeout budget per task
- Same model family when cross-system configuration allows it
- Published token pricing from the evaluation date for cost estimation

### Metrics

- Answer accuracy
- Successful reproduction rate
- Total token count
- Estimated API cost
- Wall-clock runtime

### Secondary Analysis

- Accuracy per token
- Accuracy per dollar
- Accuracy per minute
- Failure-mode profile by system

### Reporting

Use both aggregate tables and per-question breakdowns. Include at least one Pareto-style comparison showing trade-offs between accuracy, cost, and runtime.

## Artifact and Logging Plan

Each run should save:

- final answer
- structured chain or reasoning trace
- correctness label
- token usage
- estimated cost
- runtime
- blocker category if not successful
- human or judge annotations when applicable

Recommended directory layout:

```text
evaluation/
  experiments.md
  eval_runs/
    <date>-<owner>-<model>-<variant>/
      README.md
      summary.md
      chains/
      costs/
      annotations/
```

## Analysis Outputs

The final evaluation section of the project should include:

1. A main table answering RQ1 through RQ4 directly.
2. Per-paper and per-question breakdowns.
3. A missing-vs-insufficient degradation plot for RQ3.
4. A cost-token-runtime comparison table for RQ4.
5. A short qualitative error analysis with representative failure cases.

## Threats to Validity

- Some benchmark questions may reward string matching rather than real reproduction.
- Missing local assets can make a system look worse even when the reasoning is sound.
- Different agent frameworks expose different trace granularity, which can bias qualitative analysis.
- LLM-as-judge scores must be calibrated against human annotations rather than treated as ground truth.

## Recommended Execution Order

1. Finalize the exact question inventory and ground-truth mapping.
2. Freeze the evaluation settings for the single-agent and multi-agent runs.
3. Run the base RQ1 and RQ4 sweeps.
4. Build the `missing` and `insufficient` variants for RQ3 and re-run the same tasks.
5. Run the enzyme chain evaluation for RQ2.
6. Perform human annotation and agreement analysis.
7. Produce summary tables and plots for the paper.
