"""File-handoff human channel — routes ``ask_human()`` to the Claude Code session
driving the run, with NO API key and NO network.

On ``ask()`` it writes the agent's question to ``<dir>/pending.json`` and BLOCKS,
polling for ``<dir>/answer.json`` whose ``seq`` matches. The operator (the orchestrating
session) watches ``pending.json``, writes ``answer.json`` with the matching ``seq`` and a
short reply, and the blocked agent resumes. Satisfies the ``HumanChannel`` protocol
(it has an ``ask`` method), so it can be set as ``ResearchContext.human`` and the existing
``ask_human`` tool forwards questions to it.

Sequential by design: one open question at a time (the operator answers one at a time),
so a single pending/answer pair suffices. A ``seq`` counter guards against a stale
``answer.json`` being mistaken for the reply to the current question. If no answer arrives
within ``timeout`` seconds, it degrades to ``NO_HUMAN_REPLY`` (proceed autonomously) so a
run can never hang forever waiting on an operator who stepped away.
"""

import json
import os
import time
from pathlib import Path

from research_agents.hitl import NO_HUMAN_REPLY


class SessionFileHuman:
    """HumanChannel backed by a file handoff to the orchestrating session.

    The handoff directory defaults to ``$RESEARCH_ASKHUMAN_DIR`` or ``./.ask_human``
    (relative to the run's cwd — the repo root when launched by the runner), so the
    operator always knows where to look. Pass an explicit dir to override.
    """

    def __init__(
        self,
        handoff_dir: str | Path | None = None,
        poll_interval: float = 2.0,
        timeout: float = 3600.0,
    ) -> None:
        base = handoff_dir or os.environ.get("RESEARCH_ASKHUMAN_DIR") or (Path.cwd() / ".ask_human")
        self.dir = Path(base)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = float(poll_interval)
        self.timeout = float(timeout)
        self._seq = 0
        self.pending = self.dir / "pending.json"
        self.answer = self.dir / "answer.json"

    def _clear(self) -> None:
        for p in (self.pending, self.answer):
            try:
                p.unlink()
            except FileNotFoundError:
                pass

    def ask(self, question: str, *, agent: str = "") -> str:
        """Write the question for the operator and block until they answer it."""
        self._seq += 1
        seq = self._seq
        self._clear()  # start from a clean slate so we never read a stale answer
        self.pending.write_text(
            json.dumps({"seq": seq, "agent": agent, "question": question, "ts": time.time()}, indent=2),
            encoding="utf-8",
        )

        waited = 0.0
        while waited < self.timeout:
            if self.answer.exists():
                try:
                    data = json.loads(self.answer.read_text(encoding="utf-8"))
                except Exception:
                    # answer.json mid-write; wait and retry
                    time.sleep(self.poll_interval)
                    waited += self.poll_interval
                    continue
                if data.get("seq") == seq and "answer" in data:
                    reply = (data.get("answer") or "").strip()
                    self._clear()
                    return reply or "(no answer given; proceed with your best judgment)"
            time.sleep(self.poll_interval)
            waited += self.poll_interval

        # Operator never answered within the window — don't hang the run.
        self._clear()
        return NO_HUMAN_REPLY
