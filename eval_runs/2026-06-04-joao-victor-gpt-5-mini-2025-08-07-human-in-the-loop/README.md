# Human-in-the-Loop Sweep (in progress)

- Owner: Joao Victor
- Date: 2026-06-04
- Model: `gpt-5-mini-2025-08-07`
- Team: `human-in-the-loop`
- Run config: `--fresh-venv-per-question --max-turns 50`, 10-minute wall-clock cap per question
- Questions: 1 / 46 (sanity slice)
- Correct: 0 / 1
- Total tokens: 296,581
- Estimated cost: $0.0865

## Files

- `chains/`: saved chain JSON per question.
- `logs/`: terminal log per paper.
- `costs/`: copied per-paper `costs.json`.

## Per-Question Results

| ID | Ground truth | Derived | Scored answer | Correct |
| --- | --- | --- | --- | --- |
| CYTEONTO_001 | 4 | 4 | EXECUTION_REQUIRED | false |

## Note — integrity-guard downgrade (read this before scaling the sweep)

`CYTEONTO_001` is answerable only by **inspection**: the referenced CSV
`CyteOnto/notebooks/adv_tutorial/data/author_labels.csv` does not exist in the
repo. The labels are an inline list in `notebooks/adv_tutorial.ipynb`:

```python
author_labels = ["animal stem cell", "BFU-E", "CFU-M", "neutrophilic granuloblast"]  # 4 unique
```

The worker did the right thing — listed the repo, saw the CSV was missing,
searched `author_labels`, read the notebook, and counted **4** unique labels.
The critic verdict was `pass`. But triage classified the question as
`needs_execution=True`, and the worker never ran a shell command, so the
deterministic integrity guard rewrote the final answer to `EXECUTION_REQUIRED`
(scored **incorrect**).

Net: **reasoning correct, scoring incorrect.** This will systematically affect
every "load from a file that turns out to be absent / inline" question
(e.g. CYTEONTO_002, CYTEONTO_003) unless we either (a) have the worker execute a
trivial confirming command even for inspection answers, (b) relax the guard for
inspection-answerable questions, or (c) accept these as honest blocks.
