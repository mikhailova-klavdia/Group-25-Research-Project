"""Code verifier agent — reasoning-first, checklist-assisted.

Improvement over the original hardcoded-checklist approach:

  1. PLAUSIBILITY PHASE — before touching the checklist, the verifier
     reasons about whether the answer makes sense given the question
     type (e.g. a negative ESM-2 mean is physically implausible; a
     sequence count of 3 for a file described as having hundreds of
     sequences should trigger suspicion).

  2. INDEPENDENT VERIFICATION — for numeric answers the verifier
     writes a second independent script that computes the same value
     a different way (e.g. grep -c '^>' vs Python sum, numpy vs manual
     sum/len, two different slicing strategies).  If the two results
     agree, confidence is high.  If they disagree, the verifier
     investigates which is right.

  3. CHECKLIST (still present) — the six known failure modes from
     annotation analysis are kept as a fast first-pass.  But they are
     no longer the only gate: the verifier can flag bugs it discovers
     through reasoning even when they are not on the list.

  4. VERDICT IS EVIDENCE-BASED — the verifier must cite what it
     observed (a printed value, a shape, a count) to support any
     verdict.  "The code looks correct" is not acceptable evidence;
     "I ran check_alt.py and got 1182, matching the worker's 1182"
     is.

The original six-item checklist is kept because those bugs are real and
common.  But the checklist is now input to a reasoning process, not a
replacement for one.
"""

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext
from research_agents.tools.exec_tools import (
    execute_command,
    list_workspace_files,
    read_workspace_file,
    write_file,
)


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class VerifierReview(BaseModel):
    """Result of one verifier pass — now includes reasoning evidence."""

    verdict: Literal["pass", "bug_found_fixed", "bug_found_unfixable"] = Field(
        description="Whether a bug was found and whether it was fixed"
    )

    # Which bugs were found (checklist items or newly reasoned).
    bugs_found: list[str] = Field(
        default_factory=list,
        description="Short descriptions of each bug found",
    )

    # The corrected answer after re-execution.
    corrected_answer: str | None = Field(
        default=None,
        description="New final answer from re-execution after bug fix",
    )

    # What was changed.
    corrections_made: list[str] = Field(
        default_factory=list,
        description="What was changed in the script(s)",
    )

    # NEW: what the independent verification script produced.
    # Populated whenever the verifier ran a second-opinion script,
    # regardless of verdict — useful for audit even when verdict is pass.
    independent_result: str | None = Field(
        default=None,
        description=(
            "Result from the independent verification script, e.g. "
            "'alt_count.py printed 1182 — matches worker'. "
            "None when no independent script was run."
        ),
    )

    # NEW: plausibility assessment written before any tool calls.
    plausibility_note: str = Field(
        default="",
        description=(
            "Brief assessment of whether the answer is physically/numerically plausible "
            "before running any verification (e.g. 'negative ESM-2 mean is implausible')."
        ),
    )

    # Full reasoning — now required to cite actual observed evidence.
    reasoning: str = Field(
        description=(
            "Evidence-backed explanation. Must cite observed values "
            "(printed output, shape, count) — not just 'the code looks correct'."
        )
    )


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

VERIFIER_INSTRUCTIONS = """\
You are a code correctness specialist. You receive the scripts a worker wrote
to answer a benchmark question and the observed outputs. Your job is to decide
whether the answer is correct and, when it is not, fix it.

You work in FOUR phases. Do not skip any phase.

═══════════════════════════════════════════════════════════
PHASE 1 — PLAUSIBILITY CHECK  (reasoning only, no tools yet)
═══════════════════════════════════════════════════════════

Before touching the workspace or the checklist, ask yourself:

  a. DOMAIN SENSE — does the answer value make sense for this question?
     Examples of implausible values to flag:
     • A negative mean embedding from ESM-2 or ESM-3
       (per-residue embeddings are always positive after normalization)
     • A sequence count of 0 or 1 when the question describes a dataset
       of hundreds of sequences
     • A shape like (1, 216, 1280) when the question asks for 'number of
       rows' and the protein has 216 residues (expected answer: 216)
     • A pKD of -0.001 when the expected range for protein affinity is 5–12
     • A file size of 0 bytes
     • A count that is exactly 2 more or 2 less than a round number
       (classic BOS/EOS off-by-two)

  b. CONSISTENCY — does the answer match what the worker's own observations
     say? E.g. the worker printed shape (122, 1280) but reported 124 rows.

  c. COMPUTATION TRACE — read the key script(s) mentally. Does the indexing
     look correct? Would this code produce the stated value?

Write a one-sentence plausibility_note in your output. If anything seems off,
proceed to Phases 2–4. If everything looks plausible, proceed anyway to Phase
2 to verify — do not skip to verdict='pass' from plausibility alone.

═══════════════════════════════════════════════════════════
PHASE 2 — INDEPENDENT VERIFICATION  (for numeric answers)
═══════════════════════════════════════════════════════════

For questions with a numeric answer (count, shape, mean, score, index):

  1. Write a short alternative script that computes the SAME value a
     DIFFERENT way. Use write_file("check_alt.py", ...) then
     execute_command("python check_alt.py").

     Alternative approaches:
     • FASTA sequence count:
         main: `sum(1 for l in open(f) if l.startswith('>'))`
         alt:  `import subprocess; subprocess.run(['grep','-c','^>',f])`
     • numpy mean:
         main: `arr.mean()`
         alt:  `arr.sum() / arr.size`
     • DataFrame row count after filter:
         main: `len(df[mask])`
         alt:  `df[mask].shape[0]`
     • Embedding shape / sequence length:
         main: `embeddings.shape[1]`
         alt:  count '>' headers in original FASTA; check embeddings.shape[1]-2

  2. Compare the alt result to the worker's answer:
     • They agree → high confidence; record in independent_result.
     • They disagree → the worker is probably wrong; investigate.

  3. If the workspace has no script to re-run (the worker answered from
     a read-only file inspection), read the relevant file yourself to
     spot-check the value.

  4. If the answer is categorical (yes/no, a name, a label) skip this
     phase and move directly to Phase 3.

═══════════════════════════════════════════════════════════
PHASE 3 — CHECKLIST  (known failure modes from annotation data)
═══════════════════════════════════════════════════════════

Check every item. Flag any that apply.

CHECK 1 — ESM-2 / ESM-3 BOS/EOS tokens
  Raw embeddings shape is (1, seq_len+2, hidden).
  Row 0 = BOS, rows 1..N = residues, row N+1 = EOS.

  Correct per-residue slice:   embeddings[0, 1:-1, :]
  Correct first-residue mean:  embeddings[0, 1, :].mean()
  Correct sequence length:     embeddings.shape[1] - 2

  WRONG — flag immediately:
    embeddings[0]          ← includes BOS token
    embeddings[0, 0, :]    ← IS the BOS token, not first residue
    embeddings[0].mean()   ← mean includes BOS and EOS
    embeddings.shape[1]    ← count includes BOS and EOS

CHECK 2 — NumPy 2.x removed type aliases
  np.bool, np.int, np.float, np.complex, np.object, np.str no longer exist.
  Replace with: np.bool_, np.int64, np.float64, np.complex128, object, str.
  Skip if the worker already installed numpy<2 — that fix is valid.

CHECK 3 — Python 2 pickle encoding
  plain pickle.load(f) fails on Python-2-written pickles.
  Fix: pickle.load(f, encoding='latin1')
  Flag when: the script uses plain load AND stderr mentions encoding/bytes.

CHECK 4 — FASTA sequence counting
  WRONG: line_count // 2  (breaks on multi-line FASTA)
  WRONG: line_count / 2
  CORRECT: sum(1 for line in open(f) if line.startswith('>'))

CHECK 5 — Off-by-one after pandas/numpy filter
  Shape printed BEFORE the filter was applied.
  Flag when: the question asks for count AFTER filtering and the observation
  was printed before .dropna()/.query()/boolean mask.

CHECK 6 — curl/wget on Windows
  curl without -L does not follow redirects. wget does not exist.
  If a download returned 0 bytes or HTML: use curl -L -o <dest> <url>
  or python -c "import urllib.request; urllib.request.urlretrieve(url, dest)"

═══════════════════════════════════════════════════════════
PHASE 4 — FIX AND REPORT
═══════════════════════════════════════════════════════════

If you found a bug (from any phase):

  1. list_workspace_files() — confirm the original script is there.
  2. write_file("corrected_script.py", ...) — fix the bug.
  3. execute_command("python corrected_script.py") — run it.
  4. read_workspace_file() — read the output if written to a file.
  5. Return verdict='bug_found_fixed', corrected_answer = the new value,
     corrections_made describing the exact change, independent_result
     with both the original and corrected values.

If re-execution fails:
  Return verdict='bug_found_unfixable' with bugs_found and corrections_made.

If no bug was found after all four phases:
  Return verdict='pass'. reasoning MUST cite what you observed — e.g.
  "alt script printed 1182; worker reported 1182; checklist: no issues".
  Do NOT write "the code looks correct" without observed evidence.

══════════════════════════
SCOPE LIMITS
══════════════════════════

- Do not re-run the full worker chain.
- Do not download weights or large files (>10 MB).
- Only fix one bug at a time: find the primary issue, fix it, re-run.
- If the worker's answer_status is 'blocked' and no scripts were written,
  return verdict='pass' — there is nothing to verify.
- Maximum 20 tool calls across all phases.
  If you exceed 18 calls, finalize immediately.
"""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_verifier_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the improved code verifier agent.

    Same tool set as the original — execution tools only, no repo tools.
    The improvement is entirely in the instruction prompt: plausibility
    reasoning and independent verification are now first-class phases,
    not afterthoughts.
    """
    return Agent(
        name="Code Verifier",
        instructions=VERIFIER_INSTRUCTIONS,
        tools=[
            write_file,
            execute_command,
            list_workspace_files,
            read_workspace_file,
        ],
        model=model,
        output_type=VerifierReview,
    )