"""Task-local, synchronous observation of actual source-run lifecycle events."""
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Callable, Iterator
from typing import Any

_observer_error: ContextVar[BaseException | None] = ContextVar('source_observer_error', default=None)

_sink: ContextVar[Callable[..., None] | None] = ContextVar('source_run_sink', default=None)


@contextmanager
def observer_scope(sink: Callable[..., None]) -> Iterator[None]:
    """Install a run-owned sink, restoring the previous sink even on failure."""
    if not callable(sink):
        raise TypeError('source_observer_sink_must_be_callable')
    token = _sink.set(sink)
    failure_token = _observer_error.set(None)
    try:
        yield
    finally:
        _sink.reset(token)
        _observer_error.reset(failure_token)


def emit_source_event(event: str, **payload: Any) -> None:
    """Deliver original live objects; sink failures propagate unchanged."""
    sink = _sink.get()
    if sink is not None:
        try:
            sink(event, **payload)
        except BaseException as exc:
            _observer_error.set(exc)
            raise


def emit_source_failure(event: str, exception: BaseException, **payload: Any) -> None:
    """Best-effort failure notification without replacing the primary exception."""
    original_observer_error = _observer_error.get()
    try:
        emit_source_event(event, exception=exception, **payload)
    except BaseException as notification_error:
        # No recursive notification: callers re-raise the original failure.
        exception.add_note('source observer failure notification failed: '
                           + type(notification_error).__name__)
    finally:
        _observer_error.set(original_observer_error)


def is_source_observer_error(exception: BaseException) -> bool:
    """Identify the actual sink exception before a legacy error translator."""
    return _observer_error.get() is exception
