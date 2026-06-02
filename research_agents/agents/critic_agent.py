"""Critic agent for reviewing ReAct benchmark chains.

The critic is deliberately narrow: it does not use tools and does not try
to solve the benchmark question itself. It reviews the worker's visible
chain, final answer, and captured tool outputs, then returns a structured
verdict the orchestration layer can act on deterministically.
"""

from typing import Literal

from agents import Agent
from pydantic import BaseModel, Field

from research_agents.config import DEFAULT_MODEL
from research_agents.project import ResearchContext


class CriticReview(BaseModel):
    """Structured review of one worker attempt."""

    # Machine-readable decision used by orchestration to either accept
    # the worker output or perform one targeted retry.
    verdict: Literal[
        "pass",
        "redo_with_install",
        "redo_more_steps",
        "redo_with_search",
        "incorrect",
    ] = Field(description="Critic decision for the worker's current answer")

    # Human-readable rationale included in result JSON so failed benchmark
    # chains can be audited without re-running the critic.
    reasoning: str = Field(description="One-paragraph explanation of the verdict")

    # Populated only when missing imports are the actual blocker; the
    # orchestration layer may install these before retrying.
    missing_packages: list[str] = Field(
        default_factory=list,
        description="Packages or import names to install when verdict is redo_with_install",
    )

    # Short retry hint injected into the next worker prompt. Optional
    # because some verdicts terminate rather than retry.
    suggested_action: str | None = Field(
        default=None,
        description="Concise next action for the worker if a retry is allowed",
    )


CRITIC_INSTRUCTIONS = """\
You review a research agent's reasoning chain for one benchmark question.
Return one of five verdicts based only on the provided chain and captured
tool outputs:

- "pass" - the chain executed real code, observed real output, and the
  final_answer is grounded in that output. A truthful EXECUTION_REQUIRED
  final answer is also acceptable when the chain genuinely tried and was
  blocked by missing files, missing weights, GPU limits, or unavailable data,
  provided it includes a clear blocker_type, blocker_explanation, and
  blocker_evidence.
- "redo_with_install" - the chain hit ModuleNotFoundError or ImportError
  but did not try to install the missing package. Set missing_packages.
- "redo_more_steps" - the chain has fewer than 3 steps or stops at the
  EXECUTION_REQUIRED template before genuinely trying to execute.
- "redo_with_search" - the chain reports a required file was not found
  without performing an exhaustive filename/stem/parent-directory search.
- "incorrect" - the chain executed or read something, but the final_answer
  does not follow from the observations, fabricates results, or commits to
  a numeric/categorical answer not observed in real tool output.

Focus on integrity, not optimism. Do not reward README-lifted numbers,
static code-derived answers, or fabricated observations as pass. If a
benchmark question requires execution, pass only if the chain either
observed the requested value from real current-run output or honestly
reports EXECUTION_REQUIRED after a real attempt.

Blocked-answer quality:
- If the worker cannot answer, it should classify the blocker as one of
  missing_input, missing_weights, missing_dependency, external_download,
  gpu_required, runtime_error, ambiguous_question, or unknown.
- Use "redo_more_steps" when the answer is blocked but the explanation is
  vague, unsupported, or missing evidence from tool output.

Strict execution rule:
- If the question asks to run, process, merge, predict, generate, save, or
  inspect an output file, and the worker answers from README/example text,
  paper text, or static code inspection without executing the workflow or
  reading a generated artifact, the verdict MUST be "incorrect" (or
  "redo_more_steps" if a retry remains useful). This applies even when the
  answer happens to match the ground truth.
- Logic-only answers are NOT acceptable for execution questions: if the
  worker derived the answer through reasoning or formula application rather
  than actually running code and reading the output, the verdict MUST be
  "incorrect". An answer like "R = 1.5 because 50% inflation means ..." with
  no successful execute_command in the chain is fabrication, not execution.
  A "pass" verdict requires real tool output in the chain that directly
  supports the final_answer value.
- For embedding questions, distinguish raw model-token arrays from
  per-residue arrays. If the worker answers with a raw shape including
  BOS/EOS tokens when the question asks for residue rows/sequence length,
  use "incorrect".
- ESM-2 embedding sanity check: if the question involves ESM-2 per-residue
  embeddings and the worker reports a negative mean value, or reports a row
  count that is 2 more than the sequence length (i.e., includes BOS and EOS
  tokens), the verdict MUST be "incorrect". A genuine per-residue mean from
  ESM-2 is always positive (embeddings are L2-normalised representations, not
  raw logits). A row count matching sequence_length + 2 means the worker did
  not slice embeddings[1:-1] as required.
"""


def create_critic_agent(model: str = DEFAULT_MODEL) -> Agent[ResearchContext]:
    """Build the dependency and integrity critic agent."""
    return Agent(
        name="Dependency & Integrity Critic",
        instructions=CRITIC_INSTRUCTIONS,
        tools=[],
        model=model,
        output_type=CriticReview,
    )
