# Local-only trace logging for a single agent run.
#
# By default the OpenAI Agents SDK ships every span to
# platform.openai.com/traces, which requires an OpenAI dashboard login
# that this project's API-key-only setup does not have.  This module
# provides a drop-in alternative: a TracingProcessor that writes each
# span and trace event to a JSONL file on the local disk, so the run
# can be inspected with `cat` / `jq` instead of a web UI.
#
# Enabled from main.py when the user passes `--trace`; off by default
# so the SDK's built-in (unreachable) processor is not disabled for
# users who might later gain dashboard access.

import json
import threading
from pathlib import Path
from typing import Any

from agents.tracing import TracingProcessor, set_trace_processors
from agents.tracing.spans import Span
from agents.tracing.traces import Trace


class JsonlFileTraceProcessor(TracingProcessor):
    """Write every trace + span event to a single JSONL file.

    One JSON object per line; each line carries an ``event`` tag
    (``trace_start``, ``trace_end``, ``span_start``, ``span_end``) plus
    the ``data`` dict produced by the SDK's own ``.export()`` helpers.

    JSONL (append-one-per-line) is chosen over a single JSON document
    so that a crashed or interrupted run still leaves a readable file
    — everything up to the crash is already on disk, no closing bracket
    required.  The cost is that consumers must parse line-by-line, but
    that is what `jq -c` / `python -c "for line in open(...)"` expect.
    """

    def __init__(self, output_path: str | Path) -> None:
        self._output_path = Path(output_path)
        # The run dir is already created by resolve_project, so the
        # parents almost always exist — but be defensive in case this
        # processor is wired up in a different workflow later.
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        # Guard writes with a lock because the SDK may deliver span
        # callbacks concurrently from worker threads; a torn line in
        # the JSONL would make the whole file unparseable downstream.
        self._lock = threading.Lock()

    def _write_line(self, event: dict[str, Any]) -> None:
        # Open-write-close per line sacrifices a little throughput for
        # durability: a crash between two spans still leaves all prior
        # spans on disk.  At a few hundred tool calls per run the cost
        # is invisible and the simplicity is worth it.  ``default=str``
        # ensures any unexpected non-JSON-native values (datetimes,
        # Paths) round-trip as strings instead of raising.
        with self._lock:
            with self._output_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, default=str) + "\n")

    def on_trace_start(self, trace: Trace) -> None:
        self._write_line({"event": "trace_start", "data": trace.export() or {}})

    def on_trace_end(self, trace: Trace) -> None:
        self._write_line({"event": "trace_end", "data": trace.export() or {}})

    def on_span_start(self, span: Span[Any]) -> None:
        self._write_line({"event": "span_start", "data": span.export() or {}})

    def on_span_end(self, span: Span[Any]) -> None:
        self._write_line({"event": "span_end", "data": span.export() or {}})

    def shutdown(self) -> None:
        # No buffered state to flush because every line is written
        # immediately.  Implementing this is required by the interface
        # but a no-op for us.
        return None

    def force_flush(self) -> None:
        return None


def enable_local_tracing(output_path: str | Path) -> Path:
    """Replace the default trace processors with a local JSONL writer.

    Called once per process from main.py when the user passes
    ``--trace``.  ``set_trace_processors([...])`` *replaces* the
    processor list, so this also silently disables the default OpenAI
    backend — which is exactly what we want for a local-only workflow.
    Returns the resolved output path so the CLI can print it at the
    end of the run.
    """
    resolved = Path(output_path)
    set_trace_processors([JsonlFileTraceProcessor(resolved)])
    return resolved
