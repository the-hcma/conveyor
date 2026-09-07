from __future__ import annotations

import json

from django.contrib import admin
from django.db.models import Model
from django.http import HttpRequest
from django.utils.html import format_html

from .models import WebhookDelivery


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("received_at", "event", "action", "repo_full_name", "sender", "delivery_id")
    list_filter = ("event", "action", "repo_full_name", "received_at")
    search_fields = ("delivery_id", "repo_full_name", "sender")
    date_hierarchy = "received_at"
    ordering = ("-received_at",)
    readonly_fields = (
        "delivery_id",
        "event",
        "action",
        "repo_full_name",
        "sender",
        "hook_id",
        "received_at",
        "payload_pretty",
    )
    exclude = ("payload",)

    @admin.display(description="payload")
    def payload_pretty(self, obj: WebhookDelivery) -> str:
        return format_html("<pre>{}</pre>", json.dumps(obj.payload, indent=2, sort_keys=True))

    # Append-only audit log: no create/edit through the admin. Deletion stays
    # (superuser cleanup); routine aging-out is the prune_webhooks command.
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Model | None = None) -> bool:
        return False
