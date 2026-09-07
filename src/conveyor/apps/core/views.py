from __future__ import annotations

from django.db import connection
from django.http import HttpRequest, JsonResponse


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness + DB-reachability probe for the reverse proxy and deploy hook."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:  # report unhealthy, never raise from the probe
        # Drop the (likely dead) pooled connection so the next probe reconnects
        # immediately instead of reusing it for up to CONN_MAX_AGE seconds.
        connection.close()
        return JsonResponse({"status": "unhealthy", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})
