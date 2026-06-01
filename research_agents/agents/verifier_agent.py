"""Code verifier agent for catching specific numeric and indexing bugs.

The verifier is a narrow specialist inserted between the worker and critic.
It does NOT re-run the full chain — it receives the scripts the worker wrote,
checks a finite checklist of known bugs (derived from the annotation analysis
of 65 compbio chains), rewrites any buggy scripts, re-executes them in the
existing workspace, and returns a corrected answer when possible.

The checklist is intentionally small and concrete: each entry maps to a
specific failure mode observed in the benchmark data.  Adding a new entry
requires evidence from at least two annotated chain failures.
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
    """Result of one verifier pass over the worker's scripts and outputs."""

    # Machine-readable decision used by the orchestration layer.
    #   pass              — no bugs found; original answer stands
    #   bug_found_fixed   — a bug was found, a corrected script was executed,
    #                       and corrected_answer contains the new result
    #   bug_found_unfixable — a bug was found but re-execution failed or the
    #                         fix could not be determined; original answer stands
    verdict: Literal["pass", "bug_found_fixed", "bug_found_unfixable"] = Field(
        description="Whether a bug was found and whether it was fixed"
    )

    # Which checklist items fired.  Empty when verdict is 'pass'.
    bugs_found: list[str] = Field(
        default_factory=list,
        description="Short descriptions of each bug found, e.g. 'ESM-2 BOS token included in mean'",
    )

    # The corrected answer produced by re-executing the fixed script.
    # None when verdict is 'pass' or 'bug_found_unfixable'.
    corrected_answer: str | None = Field(
        default=None,
        description="New final answer from re-execution after bug fix",
    )

    # Human-readable description of what was changed.
    corrections_made: list[str] = Field(
        default_factory=list,
        description="What was changed in the script(s), e.g. 'Changed embeddings[0] to embeddings[0, 1:-1, :]'",
    )

    # Full reasoning, included in the saved chain JSON for audit.
    reasoning: str = Field(
        description="One-paragraph explanation of what was found and what was done"
    )


# ---------------------------------------------------------------------------
# Agent instructions
# ---------------------------------------------------------------------------

VERIFIER_INSTRUCTIONS = """\
You are a code correctness specialist. You receive the scripts a worker wrote
to answer a benchmark question and the outputs those scripts produced. Your job
is to check a specific bug checklist and, if you find a bug, fix it and
re-execute the corrected script to produce the right answer.

You have access to the workspace where the worker ran — all staged files are
still there. Use write_file to save a corrected script, execute_command to
run it, and read_workspace_file to inspect its output.

═══════════════════════════════════════
BUG CHECKLIST — check EVERY item
═══════════════════════════════════════

CHECK 1 — ESM-2 / ESM-3 BOS/EOS token strip
  Raw ESM embeddings have shape (1, seq_len+2, hidden) where:
    row 0       = BOS (beginning-of-sequence) special token
    row 1 to N  = actual residue embeddings (N = len(sequence))
    row N+1     = EOS (end-of-sequence) special token

  Correct per-residue slice:   embeddings[0, 1:-1, :]   (strips both)
  Correct for first residue:   embeddings[0, 1, :]       (row 1, not row 0)
  Correct sequence length:     embeddings.shape[1] - 2   (subtract BOS + EOS)

  WRONG patterns to flag:
    embeddings[0]               ← includes BOS at row 0
    embeddings[0, 0, :]         ← returns BOS token, not first residue
    embeddings[0].mean()        ← mean includes BOS and EOS
    embeddings.shape[1]         ← count includes BOS and EOS
    len(result[0])              ← if result is the raw token output

CHECK 2 — NumPy 2.x removed type aliases
  numpy 2.0 removed np.bool, np.int, np.float, np.complex, np.object, np.str.
  Any script using these will fail with AttributeError on numpy >= 2.0.

  Correct replacements:
    np.bool    → np.bool_
    np.int     → np.int64
    np.float   → np.float64
    np.complex → np.complex128
    np.object  → object
    np.str     → str

  If the worker installed numpy<2 as a workaround, do NOT flag this — the
  workaround is correct even if inelegant.

CHECK 3 — Python 2 pickle files
  pickle.load() fails on Python 2 pickles with UnicodeDecodeError or similar.
  Correct fix: pickle.load(f, encoding='latin1')
  Flag when: the script uses plain pickle.load(f) AND the error message
  mentions encoding or bytes-like object issues.

CHECK 4 — FASTA sequence counting
  Sequences in a FASTA file are separated by header lines starting with '>'.
  WRONG:  line_count // 2       ← fails for multi-line sequences
  WRONG:  line_count / 2        ← same
  CORRECT: count lines starting with '>'
    python: sum(1 for line in open(f) if line.startswith('>'))
    shell:  grep -c '^>' file.fasta

CHECK 5 — Off-by-one in pandas/numpy indexing after filtering
  A common error: the worker prints the shape of a DataFrame BEFORE dropping
  rows, then reports that as the post-filter shape. Flag when:
    - The question asks for shape/count AFTER a filter step
    - The worker printed shape before calling .dropna() / .query() / boolean mask
    - The observation shows a shape but no filter was applied before it

CHECK 6 — Curl / wget redirect failures
  On Windows, curl without -L does not follow HTTP redirects.
  wget is not available on Windows by default.
  If a download returned 0 bytes or HTML instead of the expected binary:
    Correct fix: curl -L -o <dest> <url>
    Fallback:    python -c "import urllib.request; urllib.request.urlretrieve('<url>', '<dest>')"

═══════════════════════════════════════
HOW TO FIX
═══════════════════════════════════════

When you find a bug:
1. Use list_workspace_files() to confirm the original script is still there.
2. Use write_file() to save a corrected version (e.g. corrected_script.py).
3. Use execute_command() to run the corrected script.
4. Use read_workspace_file() to inspect the output if it was written to a file.
5. Return verdict='bug_found_fixed' with corrected_answer = the new result.

If re-execution fails (import error, missing file, timeout):
  Return verdict='bug_found_unfixable' with bugs_found populated and
  corrections_made describing what you tried.

If no bug is found in any check:
  Return verdict='pass' immediately without touching any files.

═══════════════════════════════════════
SCOPE LIMITS
═══════════════════════════════════════

- Only fix bugs from the checklist above. Do not attempt general debugging.
- Do not re-download model weights or large files.
- Do not re-run the full worker chain. Only re-execute the specific script
  that contains the bug.
- If the worker used EXECUTION_REQUIRED as its answer (i.e. it never ran),
  return verdict='pass' — there is nothing to verify.
- Maximum 15 tool calls. If you cannot fix the bug in 15 calls, return
  bug_found_unfixable.
"""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_verifier_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the code verifier agent.

    The verifier is given only execution tools (write, execute, read workspace)
    — it never needs repo tools because the worker already staged everything
    into the shared workspace for this run.
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
