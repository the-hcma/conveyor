from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "conveyor.apps.core"
    label = "core"

    def ready(self) -> None:
        from conveyor.apps.core import checks  # noqa: F401  (registers system checks)
