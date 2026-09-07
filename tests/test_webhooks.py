from __future__ import annotations

import hmac
import json
from datetime import timedelta
from hashlib import sha256

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pytest_django.fixtures import Settings

from conveyor.apps.webhooks.models import WebhookDelivery
from conveyor.apps.webhooks.retention import parse_window

SECRET = "test-webhook-secret"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _webhook_secret(settings: Settings) -> None:
    settings.CONVEYOR_WEBHOOK_SECRET = SECRET


def _sign(body: bytes, secret: str = SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, sha256).hexdigest()


def _post(
    payload: dict,
    *,
    delivery: str = "d-1",
    event: str = "push",
    signature: str | None = None,
    sign: bool = True,
):
    body = json.dumps(payload).encode()
    headers = {"X-GitHub-Delivery": delivery, "X-GitHub-Event": event}
    if signature is not None:
        headers["X-Hub-Signature-256"] = signature
    elif sign:
        headers["X-Hub-Signature-256"] = _sign(body)
    return Client().post(
        reverse("github-webhook"), data=body, content_type="application/json", headers=headers
    )


class TestIngestion:
    def test_valid_delivery_is_accepted_and_stored(self) -> None:
        payload = {
            "action": "opened",
            "repository": {"full_name": "the-hcma/blumkin"},
            "sender": {"login": "octocat"},
        }
        resp = _post(payload, event="pull_request", delivery="abc-123")
        assert resp.status_code == 202
        assert resp.json() == {"status": "accepted", "delivery_id": "abc-123"}

        row = WebhookDelivery.objects.get(delivery_id="abc-123")
        assert row.event == "pull_request"
        assert row.action == "opened"
        assert row.repo_full_name == "the-hcma/blumkin"
        assert row.sender == "octocat"
        assert row.payload == payload

    def test_bad_signature_is_rejected(self) -> None:
        resp = _post({"a": 1}, signature="sha256=deadbeef")
        assert resp.status_code == 401
        assert not WebhookDelivery.objects.exists()

    def test_missing_signature_is_rejected(self) -> None:
        resp = _post({"a": 1}, sign=False)
        assert resp.status_code == 401
        assert not WebhookDelivery.objects.exists()

    def test_duplicate_delivery_is_deduped(self) -> None:
        first = _post({"action": "x"}, delivery="dup-1")
        second = _post({"action": "x"}, delivery="dup-1")
        assert first.status_code == 202
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"
        assert WebhookDelivery.objects.filter(delivery_id="dup-1").count() == 1

    def test_invalid_json_is_rejected(self) -> None:
        body = b"{not json"
        resp = Client().post(
            reverse("github-webhook"),
            data=body,
            content_type="application/json",
            headers={
                "X-GitHub-Delivery": "j-1",
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": _sign(body),
            },
        )
        assert resp.status_code == 400
        assert not WebhookDelivery.objects.exists()

    def test_missing_github_headers_is_rejected(self) -> None:
        body = b"{}"
        resp = Client().post(
            reverse("github-webhook"),
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": _sign(body)},
        )
        assert resp.status_code == 400

    def test_get_is_not_allowed(self) -> None:
        assert Client().get(reverse("github-webhook")).status_code == 405

    def test_overlong_payload_metadata_is_truncated(self) -> None:
        payload = {
            "repository": {"full_name": "x" * 500},
            "sender": {"login": "y" * 500},
            "action": "z" * 200,
        }
        resp = _post(payload, delivery="clip-1")
        assert resp.status_code == 202
        row = WebhookDelivery.objects.get(delivery_id="clip-1")
        assert len(row.repo_full_name) == 255
        assert len(row.sender) == 255
        assert len(row.action) == 64

    def test_overlong_event_header_is_rejected(self) -> None:
        resp = _post({"a": 1}, event="e" * 100, delivery="clip-2")
        assert resp.status_code == 400
        assert not WebhookDelivery.objects.filter(delivery_id="clip-2").exists()

    def test_secret_unset_returns_503(self, settings: Settings) -> None:
        settings.CONVEYOR_WEBHOOK_SECRET = ""
        assert _post({"a": 1}, sign=False).status_code == 503


class TestParseWindow:
    @pytest.mark.parametrize(
        ("spec", "expected"),
        [("14d", timedelta(days=14)), ("36h", timedelta(hours=36)), ("2w", timedelta(weeks=2))],
    )
    def test_valid(self, spec: str, expected: timedelta) -> None:
        assert parse_window(spec) == expected

    @pytest.mark.parametrize("spec", ["", "14", "d", "0d", "-1d", "14 days", "10y"])
    def test_invalid_raises(self, spec: str) -> None:
        with pytest.raises(ValueError):
            parse_window(spec)


def test_prune_webhooks_deletes_only_stale_rows() -> None:
    fresh = WebhookDelivery.objects.create(delivery_id="fresh", event="push", payload={})
    stale = WebhookDelivery.objects.create(delivery_id="stale", event="push", payload={})
    WebhookDelivery.objects.filter(pk=stale.pk).update(
        received_at=timezone.now() - timedelta(days=30)
    )

    call_command("prune_webhooks", "--window", "14d", "--dry-run")
    assert WebhookDelivery.objects.count() == 2  # dry-run deletes nothing

    call_command("prune_webhooks", "--window", "14d")
    remaining = list(WebhookDelivery.objects.values_list("delivery_id", flat=True))
    assert remaining == [fresh.delivery_id]
