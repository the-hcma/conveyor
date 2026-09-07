from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_healthz_ok() -> None:
    response = Client().get(reverse("healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_url_is_wired() -> None:
    assert reverse("admin:index") == "/admin/"
