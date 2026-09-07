from __future__ import annotations

from django.db import models


class WebhookDelivery(models.Model):
    """One GitHub webhook delivery, stored verbatim.

    The hot tier: rows are pruned past ``CONVEYOR_HOT_WINDOW`` by the
    ``prune_webhooks`` command (from M3 the delivery also lives on in Redpanda).
    Append-only — nothing mutates a row after ingestion.
    """

    delivery_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="GitHub's X-GitHub-Delivery GUID; the idempotency key.",
    )
    event = models.CharField(max_length=64, db_index=True, help_text="X-GitHub-Event.")
    action = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="payload.action, when the event has one.",
    )
    repo_full_name = models.CharField(max_length=255, blank=True, db_index=True)
    sender = models.CharField(max_length=255, blank=True)
    hook_id = models.CharField(max_length=64, blank=True, help_text="X-GitHub-Hook-ID.")
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    payload = models.JSONField()

    class Meta:
        ordering = ("-received_at",)
        indexes = [
            models.Index(fields=["repo_full_name", "event", "-received_at"]),
        ]

    def __str__(self) -> str:
        tail = f".{self.action}" if self.action else ""
        return f"{self.event}{tail} {self.repo_full_name} ({self.delivery_id})"
