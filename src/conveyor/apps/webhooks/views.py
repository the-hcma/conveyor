from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .ingest import WebhookError, ingest


@csrf_exempt
def github_webhook(request: HttpRequest) -> JsonResponse | HttpResponseNotAllowed:
    """Receive a GitHub webhook delivery: verify HMAC, dedupe, store."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    headers = {
        "signature": request.headers.get("X-Hub-Signature-256"),
        "delivery": request.headers.get("X-GitHub-Delivery"),
        "event": request.headers.get("X-GitHub-Event"),
        "hook_id": request.headers.get("X-GitHub-Hook-ID"),
    }

    try:
        result = ingest(settings.CONVEYOR_WEBHOOK_SECRET, request.body, headers)
    except WebhookError as exc:
        return JsonResponse({"status": "rejected", "detail": exc.detail}, status=exc.status)

    return JsonResponse(
        {
            "status": "accepted" if result.created else "duplicate",
            "delivery_id": result.delivery.delivery_id,
        },
        status=202 if result.created else 200,
    )
