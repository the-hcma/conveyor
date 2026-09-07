from __future__ import annotations

import pytest
from django.test import Client, override_settings
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_ok() -> None:
    response = Client().get(reverse("healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_url_is_wired() -> None:
    assert reverse("admin:index") == "/admin/"


class TestSecretKeyCheck:
    """conveyor.E001 — the insecure dev key must fail a non-DEBUG process."""

    @staticmethod
    def _run() -> list[str]:
        from conveyor.apps.core.checks import conveyor_secret_key_check

        return [str(e.id) for e in conveyor_secret_key_check(None)]

    @override_settings(DEBUG=False, SECRET_KEY="django-insecure-local-dev-only")
    def test_fires_when_debug_off_and_key_insecure(self) -> None:
        assert self._run() == ["conveyor.E001"]

    @override_settings(DEBUG=True, SECRET_KEY="django-insecure-local-dev-only")
    def test_silent_when_debug_on(self) -> None:
        assert self._run() == []

    @override_settings(DEBUG=False, SECRET_KEY="a-real-injected-secret-key")
    def test_silent_with_a_real_key(self) -> None:
        assert self._run() == []
