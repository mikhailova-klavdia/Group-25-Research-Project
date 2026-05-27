# Claude Evaluator Prompt

Paste this prompt into a fresh Claude Code session (pointed at this repo root) to run the
independent chain evaluation. The session needs read access to the local `papers/` directory.

Re-run at the start of each iteration to get updated frequency counts and diagnostics.

---

```
You are a research evaluator for a paper-reproduction agent system. Your job is a
three-phase independent analysis. Work methodically through all phases in order.

## Context

Project root: C:\Users\32472\Desktop\MaastrichtUni\MscAI\ProjectSem2\Phase3\Group-25-Research-Project

This project has an OpenAI-Agents-SDK-based ReAct agent (research_agents/agents/react_agent.py,
research_agents/react_main.py) that was run against 22 questions across 4 bioRxiv repos.
The generated chains are stored in question-answers/ at the repo root.

The 4 repos and their papers are locally available:
- papers/PPLM/paper.pdf + papers/PPLM/repo/
- papers/CrossPPI/paper.pdf + papers/CrossPPI/repo/
- papers/metapointfinder/paper.pdf + papers/metapointfinder/repo/
- papers/SKiM-GPT/paper.pdf + papers/SKiM-GPT/repo/

Question files (read these to get the 22 questions and ground truths):
- question-answers/PPLM.json
- question-answers/CROSSPPI.json
- question-answers/METAPOINT.json
- question-answers/SKIMGPT.json

Chain output files (one per question, produced by react_main.py):
Find them under papers/<slug>/runs/. Each file is named <ID>.json and contains
the full T/A/O/R chain, final_answer, ground_truth, and a heuristic correct flag.
List all 22 chain files before starting Phase 1.

---

## Phase 1 — Independent Attempts (DO THIS BEFORE READING THE CHAINS)

For each of the 22 questions:

1. Read the relevant paper.pdf (use pdfminer, PyMuPDF, or read it as text)
2. Explore the repo (list files, read README, main scripts, config)
3. Attempt to answer the question yourself using explicit Thought → Action → Observation →
   Reflection steps, written out in full
4. Give your own final answer

Do NOT read the stored chains in papers/<slug>/runs/ until all 22 are attempted.

---

## Phase 2 — Chain Comparison

Now read the 22 stored chain JSON files.

For each chain compare:
- The GPT agent's reasoning path vs. your own attempt
- Whether the final answer matches the ground truth
- Where the GPT agent diverged from what you found
- Whether the agent's observations appear real (verifiable against repo) or fabricated

---

## Phase 3 — Exhaustive Error Analysis + Diagnostics

### A. Per-chain error table
For each of the 22 chains: ID, question summary, correct (yes/no), list of error types
found, most critical failure step (step number + one-line description).

Apply this error taxonomy (flag any that apply; add new types if you discover them):
- E1: Observation Fabrication — agent claims output/files that do not exist
- E2: Path Substitution — wrong file path used
- E3: Synthetic Data — numbers invented rather than produced by execution
- E4: Wrong Methodology — correct goal, wrong tool or command
- E5: Syntax Corruption — agent-written code has syntax or import errors
- E6: Numeric Overconfidence — specific value stated without running the experiment
- E7: Premature Termination — agent stops before fully answering
- E8: Missing Path Verification — file assumed to exist without confirmation
- [Add any new types discovered]

### B. Frequency table
Produce a table with one row per error type: error ID, name, and the number of chains
(out of 22) in which that error type appears. Sort by frequency descending.

### C. Cross-repo patterns
Which error types are most frequent? Are there repo-specific failure modes?
Does the agent fail consistently on certain question types (execution vs. factual vs. numeric)?

### D. Iteration-1 focus
List the top 3 error types by frequency. For each: one concrete, actionable fix to the
agent prompt or tool design that would address it.

### E. SDK / codebase inspection
Read research_agents/agents/react_agent.py, research_agents/react_main.py,
research_agents/tools/exec_tools.py, research_agents/tools/repo_tools.py,
research_agents/project.py.

Then locate the installed openai-agents SDK source:
  python -c "import agents; print(agents.__file__)"

Identify:
- Structural limitations in how the SDK handles tool results (truncation, error swallowing)
- Whether the ReAct loop gives the model enough context to self-correct
- Prompt/instruction gaps that explain observed failures
- Concrete changes to address the top 3 failure modes

---

## Output

Write the full Phase 3 report (sections A–E) to:
C:\Users\32472\Desktop\MaastrichtUni\MscAI\ProjectSem2\Phase3\ClaudeEvalReport.md

Include a short executive summary at the top (5–8 bullet points, most critical findings).
```
