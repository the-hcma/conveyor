from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.core.checks import Error, register


@register
def conveyor_secret_key_check(app_configs: Any, **kwargs: Any) -> Sequence[Error]:
    """Fail on any non-DEBUG process still using the insecure development key.

    Registered as a normal system check (not ``deploy=True``), so it runs on
    every ``manage.py`` command — server start, ``migrate``, CI ``check`` — and a
    production process cannot boot on the ``django-insecure-`` fallback key.
    """
    if not settings.DEBUG and str(settings.SECRET_KEY).startswith("django-insecure-"):
        return [
            Error(
                "CONVEYOR_SECRET_KEY is unset — running with DEBUG off on the insecure "
                "development key. Set a real key in the environment.",
                id="conveyor.E001",
            )
        ]
    return []


@register
def conveyor_webhook_secret_check(app_configs: Any, **kwargs: Any) -> Sequence[Error]:
    """Fail a non-DEBUG process with no webhook secret — ingestion cannot verify."""
    if not settings.DEBUG and not settings.CONVEYOR_WEBHOOK_SECRET:
        return [
            Error(
                "CONVEYOR_WEBHOOK_SECRET is unset with DEBUG off — POST /webhooks/github "
                "will reject every delivery (503).",
                id="conveyor.E002",
            )
        ]
    return []
