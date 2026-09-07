from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from conveyor.apps.webhooks.models import WebhookDelivery
from conveyor.apps.webhooks.retention import parse_window


class Command(BaseCommand):
    help = "Delete WebhookDelivery rows older than CONVEYOR_HOT_WINDOW (the hot tier)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--window",
            default=settings.CONVEYOR_HOT_WINDOW,
            help=f"retention window (default CONVEYOR_HOT_WINDOW: {settings.CONVEYOR_HOT_WINDOW})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would be deleted without deleting.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        cutoff = timezone.now() - parse_window(options["window"])
        stale = WebhookDelivery.objects.filter(received_at__lt=cutoff)
        count = stale.count()

        if options["dry_run"]:
            self.stdout.write(f"[dry-run] {count} delivery(ies) older than {cutoff.isoformat()}")
            return

        stale.delete()
        self.stdout.write(f"pruned {count} delivery(ies) older than {cutoff.isoformat()}")
