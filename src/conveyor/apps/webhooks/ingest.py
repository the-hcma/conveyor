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
    if not hmac.compare_digest(expected, signature_header):
        raise WebhookError(401, "signature mismatch")


def _payload_str(payload: dict[str, Any], *path: str) -> str:
    node: Any = payload
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    return node if isinstance(node, str) else ""


def ingest(secret: str, body: bytes, headers: dict[str, str | None]) -> IngestResult:
    """Verify, parse, dedupe and persist one delivery.

    ``headers`` keys: ``signature``, ``delivery``, ``event``, ``hook_id``.
    """
    verify_signature(secret, body, headers.get("signature"))

    delivery_id = headers.get("delivery")
    event = headers.get("event")
    if not delivery_id or not event:
        raise WebhookError(400, "missing X-GitHub-Delivery or X-GitHub-Event")

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
            "action": _payload_str(payload, "action"),
            "repo_full_name": _payload_str(payload, "repository", "full_name"),
            "sender": _payload_str(payload, "sender", "login"),
            "hook_id": headers.get("hook_id") or "",
            "payload": payload,
        },
    )
    return IngestResult(delivery=delivery, created=created)
