"""Redact trial diagnostics without corrupting access-log records."""

from contextvars import ContextVar
import logging


trial_request = ContextVar("trial_request", default=False)


class TrialLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Uvicorn's access formatter expects the original five arguments:
        # client address, request line, status code, response size and duration.
        # Never alter access records.
        if record.name == "uvicorn.access":
            return True

        if trial_request.get():
            # SQL/parse exceptions may contain raw input as exception parameters.
            record.msg = "Trial service diagnostic (details redacted)"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None

        return True


def install() -> None:
    previous = logging.getLogRecordFactory()

    if getattr(previous, "demo_filtered", False):
        return

    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        TrialLogFilter().filter(record)
        return record

    factory.demo_filtered = True
    logging.setLogRecordFactory(factory)