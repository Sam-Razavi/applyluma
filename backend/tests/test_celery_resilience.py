"""Tests for the Celery worker's resilience to corrupted broker messages.

A producer that pushes a raw payload onto the queue (e.g. a bare
``redis.lpush("celery", json.dumps(...))``) creates a message without the Kombu
envelope. Importing ``app.tasks.celery_app`` installs a guard around
``kombu.transport.virtual.Message.__init__`` so such a message is logged and
discarded instead of raising ``KeyError('properties')`` and crashing the worker.
"""
import logging

from kombu.transport import virtual

# Importing the module applies the resilience monkeypatch.
import app.tasks.celery_app  # noqa: F401


def test_message_missing_properties_is_logged_and_not_fatal(caplog):
    """A payload with no Kombu envelope must not raise; it is logged + discarded."""
    malformed = {
        "task": "app.tasks.matching.compute_job_matching_scores",
        "id": "match-1",
        "args": ["user-1"],
        "kwargs": {},
    }  # no 'properties' / 'headers' / 'body' — the exact shape a raw lpush produces

    with caplog.at_level(logging.ERROR):
        # Must NOT raise KeyError('properties').
        msg = virtual.Message(malformed, channel=None)

    assert "corrupted broker message" in caplog.text
    # Defaults were filled in so construction succeeded without crashing.
    assert msg.properties.get("delivery_tag")


def test_well_formed_message_is_unaffected():
    """A message that already has the envelope constructs normally, no logging."""
    payload = {
        "body": None,
        "properties": {"delivery_tag": "abc-123"},
        "headers": {},
        "content-type": "application/json",
        "content-encoding": "utf-8",
    }

    msg = virtual.Message(payload, channel=None)

    assert msg.properties.get("delivery_tag") == "abc-123"
