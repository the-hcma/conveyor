from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.core.checks import Error, register


@register(deploy=True)
def conveyor_deploy_checks(app_configs: Any, **kwargs: Any) -> Sequence[Error]:
    errors: list[Error] = []
    if str(settings.SECRET_KEY).startswith("django-insecure-"):
        errors.append(
            Error(
                "CONVEYOR_SECRET_KEY is unset — running on the insecure development key.",
                id="conveyor.E001",
            )
        )
    if not settings.CONVEYOR_WEBHOOK_SECRET:
        errors.append(
            Error(
                "CONVEYOR_WEBHOOK_SECRET is unset — webhook signature verification cannot run.",
                id="conveyor.E002",
            )
        )
    return errors
