"""taskiq middlewares for InfraCanvas worker observability + reliability.

Three middlewares are layered on the broker (see :mod:`app.queue.broker`):

* :class:`RequestIdMiddleware` — re-binds ``request_id`` (and ``scan_id`` if
  present as the first positional arg) from the task's labels into the
  worker-side ``structlog`` contextvar so every log line emitted inside the
  task body shares the same trace id as the originating HTTP request.
  Implements D-21 (single-trace-id observability across sync→async boundary).

* :class:`SentryTaskMiddleware` — tags the active Sentry scope with the task
  name + request_id and captures any exception bubbled by the task body.

* :class:`DLQLogMiddleware` — when SmartRetryMiddleware's retry budget is
  exhausted, emit a structured log line with ``dlq=true`` so on-call sees
  the dead-letter event in the log drain. RESEARCH § F7 calls log-as-DLQ
  sufficient for Phase 6; a Redis-list DLQ is a Phase 8 concern.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
import structlog
from taskiq import TaskiqMiddleware
from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult

_log = structlog.get_logger("app.worker")


class RequestIdMiddleware(TaskiqMiddleware):
    """Re-bind request_id (+ scan_id) from task labels into structlog contextvar.

    The HTTP-side handler attaches ``request_id`` via the kicker:
    ``task.kicker().with_labels(request_id=rid).kiq(...)``. By the time the
    worker process pops the message off Redis, the original asyncio task
    that owned the contextvar is gone — we must explicitly rebind here so
    ``merge_contextvars`` (in :mod:`app.obs.logging`) emits the same trace id
    in worker-side logs.
    """

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        # Always start clean: contextvars survive across awaits in the worker
        # event loop, so a previous task's bindings could leak otherwise.
        structlog.contextvars.clear_contextvars()
        labels = message.labels or {}
        rid = labels.get("request_id", "") if isinstance(labels, dict) else ""
        if rid:
            structlog.contextvars.bind_contextvars(request_id=rid)
        # Convenience: many indexing tasks carry scan_id as the first
        # positional arg. Bind it eagerly so log lines inside the task body
        # carry both keys.
        if message.args and isinstance(message.args[0], str):
            structlog.contextvars.bind_contextvars(scan_id=message.args[0])
        return message

    async def post_execute(
        self, message: TaskiqMessage, result: TaskiqResult[Any]
    ) -> None:
        # Defensive: clear so the next task picked up by this worker loop
        # starts with no leaked context. (taskiq does NOT spawn fresh tasks
        # per message in InMemoryBroker; the same coroutine runs them.)
        structlog.contextvars.clear_contextvars()


class DLQLogMiddleware(TaskiqMiddleware):
    """Emit a ``dlq=true`` structured log when SmartRetryMiddleware exhausts retries.

    SmartRetryMiddleware tracks the retry counter via the ``_retry_count``
    label on the rescheduled message. When the counter reaches the
    ``max_retries`` configured for the task, the next failure has no further
    rescheduling — the task is definitively dead. We detect that condition
    here in ``on_error`` and emit a structured event so the log drain
    (Vector → BetterStack per Plan 02) surfaces it for on-call.
    """

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:
        labels = message.labels or {}
        if not isinstance(labels, dict):
            labels = {}
        retry_count = int(labels.get("_retry_count", 0) or 0)
        # ``max_retries`` is set on the task decorator; SmartRetryMiddleware
        # also reads from labels. Default to 3 to match broker config.
        max_retries = int(labels.get("max_retries", 3) or 3)
        if retry_count >= max_retries:
            _log.error(
                "task_dlq",
                dlq=True,
                task_name=message.task_name,
                args=message.args,
                kwargs=message.kwargs,
                error=repr(exception),
                request_id=labels.get("request_id", ""),
            )


class SentryTaskMiddleware(TaskiqMiddleware):
    """Mirror the HTTP Sentry scope onto worker tasks: tag + capture.

    ``pre_execute`` tags the scope with ``task_name`` + ``request_id`` so
    Sentry events dropped during this task carry the same correlation id as
    the originating request. ``on_error`` captures any uncaught exception so
    even tasks that swallow errors at the application layer surface in
    Sentry.
    """

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        sentry_sdk.set_tag("task_name", message.task_name)
        labels = message.labels or {}
        if isinstance(labels, dict) and labels.get("request_id"):
            sentry_sdk.set_tag("request_id", labels["request_id"])
        return message

    async def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult[Any],
        exception: BaseException,
    ) -> None:
        sentry_sdk.capture_exception(exception)
