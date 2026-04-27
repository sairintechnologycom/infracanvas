"""Module-level taskiq broker — imported by the worker CLI and HTTP handlers.

Topology (RESEARCH § F7):

* :class:`taskiq_redis.ListQueueBroker` against ``settings.redis_url``
  (Upstash). ``ListQueueBroker`` uses Redis lists with ``BLPOP`` for durable
  queueing — NOT ``PubSubBroker``, which drops messages if no worker is
  attached at publish time.
* :class:`taskiq_redis.RedisAsyncResultBackend` with ``keep_results=3600``
  (1-hour TTL) so callers can fetch task results without permanently
  growing Redis state.
* Middleware order is intentional:

    1. :class:`SmartRetryMiddleware` — schedules retries with exponential
       backoff + jitter. Wraps the task body so retries fire BEFORE the
       observability middlewares record terminal state.
    2. :class:`RequestIdMiddleware` — binds the trace id at the start of
       each (re-)execution so retries log under the same request_id.
    3. :class:`SentryTaskMiddleware` — tags Sentry scope at task start;
       captures exceptions on error.
    4. :class:`DLQLogMiddleware` — LAST so it observes post-retry state.
       Its ``on_error`` runs after SmartRetry has decided whether to
       reschedule; if the retry budget is exhausted, this emits the
       ``dlq=true`` structured log line.

The broker is a module-level singleton because the taskiq worker CLI
imports it via ``taskiq worker app.queue.broker:broker`` — i.e. as a
process-wide entry point.
"""

from __future__ import annotations

from taskiq import TaskiqEvents
from taskiq.middlewares import SmartRetryMiddleware
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.queue.middleware import (
    DLQLogMiddleware,
    RequestIdMiddleware,
    SentryTaskMiddleware,
)
from app.settings import settings

# Durable queue (BLPOP-based) — survives a worker restart since the messages
# remain enqueued on Redis until ack'd.
broker = (
    ListQueueBroker(settings.redis_url, queue_name="infracanvas:tasks")
    .with_result_backend(
        RedisAsyncResultBackend(settings.redis_url, keep_results=3600)
    )
    .with_middlewares(
        # 3 retries with 5s base delay, jitter on, exponential backoff capped
        # at 120s — RESEARCH § F7 lines 509-529. Suitable for transient R2 /
        # Postgres / Stripe blips; not suitable for infinite retry of a
        # malformed payload (those should bubble to the DLQ log).
        SmartRetryMiddleware(
            default_retry_count=3,
            default_delay=5,
            use_jitter=True,
            use_delay_exponent=True,
            max_delay_exponent=120,
        ),
        RequestIdMiddleware(),
        SentryTaskMiddleware(),
        DLQLogMiddleware(),  # LAST: observes post-retry state
    )
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _configure_worker_logging(_state: object) -> None:
    """Re-run :func:`app.obs.logging.configure_logging` in the worker process.

    The HTTP process configures logging at app startup; the worker process
    is a separate Python process spawned by ``taskiq worker``, so it must
    run the same configuration. Idempotent thanks to
    ``cache_logger_on_first_use=True``.
    """
    from app.obs.logging import configure_logging

    configure_logging()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _init_worker_sentry(_state: object) -> None:
    """Initialise Sentry in the worker process with ``process_role=worker``.

    The HTTP and worker processes are separate Python interpreters, so
    Sentry's SDK has to be initialised in each. The ``process_role`` tag
    distinguishes the two in the Sentry UI when triaging an incident.
    """
    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.env,
            release=settings.git_sha,
            traces_sample_rate=0.1,
        )
        sentry_sdk.set_tag("process_role", "worker")
