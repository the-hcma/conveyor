"""GitHub webhook ingestion — signature check, dedupe, store.

Kept transport-agnostic (operates on raw bytes + a header getter) so the view is
thin and the logic is directly unit-testable.
"""

from __future__ import annotations

import hmac
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .models import WebhookDelivery

_SIGNATURE_PREFIX = "sha256="


class WebhookError(Exception):
    """Ingestion rejected. ``status`` is the HTTP code the view should return."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class IngestResult:
    delivery: WebhookDelivery
    created: bool


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> None:
    """Constant-time check of ``X-Hub-Signature-256`` against the shared secret."""
    if not secret:
        raise WebhookError(503, "CONVEYOR_WEBHOOK_SECRET is not configured")
    if not signature_header or not signature_header.startswith(_SIGNATURE_PREFIX):
        raise WebhookError(401, "missing or malformed X-Hub-Signature-256")
    expected = _SIGNATURE_PREFIX + hmac.new(secret.encode(), body, sha256).hexdigest()
    # Compare as bytes: a valid signature is ASCII hex, and WSGI hands us the
    # header Latin-1-decoded — hmac.compare_digest(str, str) raises TypeError on
    # any non-ASCII char, which would 500 an unauthenticated endpoint. "replace"
    # maps non-ASCII to a byte that cannot match, i.e. a clean 401.
    if not hmac.compare_digest(
        expected.encode("ascii"), signature_header.encode("ascii", "replace")
    ):
        raise WebhookError(401, "signature mismatch")


def _field_len(name: str) -> int:
    return WebhookDelivery._meta.get_field(name).max_length  # type: ignore[attr-defined,return-value]


def _payload_str(payload: dict[str, Any], field: str, *path: str) -> str:
    node: Any = payload
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    value = node if isinstance(node, str) else ""
    # Postgres enforces varchar length (SQLite does not) — truncate cosmetic
    # metadata rather than let an oversized value 500 the write and make GitHub
    # retry the delivery forever.
    return value[: _field_len(field)]


def ingest(secret: str, body: bytes, headers: dict[str, str | None]) -> IngestResult:
    """Verify, parse, dedupe and persist one delivery.

    ``headers`` keys: ``signature``, ``delivery``, ``event``, ``hook_id``.
    """
    verify_signature(secret, body, headers.get("signature"))

    delivery_id = headers.get("delivery")
    event = headers.get("event")
    if not delivery_id or not event:
        raise WebhookError(400, "missing X-GitHub-Delivery or X-GitHub-Event")
    # delivery_id and event are load-bearing — reject rather than truncate a
    # value no real GitHub delivery produces (a truncated idempotency key could
    # collide with a different delivery).
    if len(delivery_id) > _field_len("delivery_id"):
        raise WebhookError(400, "X-GitHub-Delivery exceeds the maximum length")
    if len(event) > _field_len("event"):
        raise WebhookError(400, "X-GitHub-Event exceeds the maximum length")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise WebhookError(400, f"invalid JSON body: {exc}") from exc
    if not isinstance(payload, dict):
        raise WebhookError(400, "webhook payload must be a JSON object")

    delivery, created = WebhookDelivery.objects.get_or_create(
        delivery_id=delivery_id,
        defaults={
            "event": event,
            "action": _payload_str(payload, "action", "action"),
            "repo_full_name": _payload_str(payload, "repo_full_name", "repository", "full_name"),
            "sender": _payload_str(payload, "sender", "sender", "login"),
            "hook_id": (headers.get("hook_id") or "")[: _field_len("hook_id")],
            "payload": payload,
        },
    )
    return IngestResult(delivery=delivery, created=created)
