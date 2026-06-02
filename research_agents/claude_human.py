"""Claude-backed human-in-the-loop channel for autonomous operator decisions.

Satisfies the HumanChannel protocol so it can be attached to ResearchContext.human.
When an agent calls ask_human(), this class forwards the question to the Claude API
with a system prompt that positions Claude as an expert operator for computational
biology paper reproduction.  The reply is short and actionable — it is read by the
downstream agent as tool output, not as a document.

Requires ANTHROPIC_API_KEY in the environment (add it to .env alongside
OPENAI_API_KEY).
"""

import anthropic

# Keep replies tight: the agent reads the answer as a tool-call result and should
# act on it immediately.  A wall of text wastes turns and obscures the decision.
_MAX_TOKENS = 512

# Positions Claude as a practical operator rather than a chatbot.  The bullet list
# covers the most common blockers so Claude knows the expected action space without
# the prompt having to enumerate every edge case.
_SYSTEM_PROMPT = """\
You are an expert human operator helping AI agents reproduce computational biology \
papers. An AI agent is stuck and has asked you for a concrete decision or workaround. \
Give a short, actionable answer — one to three sentences at most. Do not explain at \
length; just state what to do.

Common situations and good answers:
• A Python package fails to install (version conflict, build error): suggest an \
  alternative version or a compatible open-source replacement.
• A model requires a license token or API key: suggest the equivalent open-weight \
  variant (e.g. "use TabPFN-v2 open weights, which need no token", "use the \
  HuggingFace open-access checkpoint").
• A dataset or weight file is missing and would need re-generation: decide whether \
  to regenerate it with the paper's stated seed (if deterministic) or to block.
• The question is ambiguous: interpret it in the most literal, computationally \
  testable way.
• A GPU-only operation is required but no GPU is available: suggest the CPU fallback \
  flag, or mark the step as not-possible.
• The agent proposes an expensive or irreversible action: give a clear go/no-go.

Always be concrete. Never say "it depends". If you are genuinely unsure, give your \
best guess and flag it briefly (≤5 words).\
"""


class ClaudeHuman:
    """Human-channel implementation backed by the Claude API.

    Satisfies the HumanChannel protocol (has an ``ask`` method) so it can be set
    as ``ResearchContext.human`` and the existing ask_human tool forwards agent
    questions to Claude instead of blocking on stdin or returning NO_HUMAN_REPLY.

    A single Anthropic client is created on first use so the SDK's connection pool
    is reused across all ask() calls within a single question run.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        # Defer client construction to first ask() so importing this module
        # (e.g. in tests) does not fail when ANTHROPIC_API_KEY is absent.
        self._model = model
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        """Return the shared client, creating it on first use."""
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def ask(self, question: str, *, agent: str = "") -> str:
        """Forward the agent's question to Claude and return a concrete answer.

        ``agent`` is prepended in brackets when non-empty so Claude can see which
        stage (triage / setup / execution) is asking — useful context when the same
        session has multiple agents calling ask_human.  API errors degrade to a
        "proceed autonomously" message rather than crashing the run.
        """
        user_content = f"[{agent}] {question}" if agent else question
        try:
            message = self._get_client().messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            return message.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001
            # Any API failure (auth, rate limit, network) must not crash the
            # evaluation run — degrade to autonomous with a note about the error.
            return (
                f"CLAUDE_HUMAN_ERROR: {type(exc).__name__}: {exc}. "
                "Proceed autonomously using your best judgment."
            )
