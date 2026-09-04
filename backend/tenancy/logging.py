import logging
import threading

_thread_locals = threading.local()


def set_current_request_id(request_id: str | None) -> None:
    _thread_locals.request_id = request_id


def get_current_request_id() -> str:
    return getattr(_thread_locals, "request_id", "-") or "-"


class RequestIDFilter(logging.Filter):
    """
    Injects the active request ID into log records for structured observability.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_current_request_id()
        return True
