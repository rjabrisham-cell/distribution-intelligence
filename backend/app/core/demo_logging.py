"""Redact legacy service diagnostics only while handling a public Trial request."""
from contextvars import ContextVar
import logging

trial_request = ContextVar("trial_request", default=False)


class TrialLogFilter(logging.Filter):
    def filter(self, record):
        if trial_request.get():
            # SQL/parse exceptions may contain raw input as exception parameters.
            record.msg = "Trial service diagnostic (details redacted)"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def install():
    previous = logging.getLogRecordFactory()
    if getattr(previous, "demo_filtered", False):
        return
    def factory(*args, **kwargs):
        record = previous(*args, **kwargs)
        TrialLogFilter().filter(record)
        return record
    factory.demo_filtered = True
    logging.setLogRecordFactory(factory)
