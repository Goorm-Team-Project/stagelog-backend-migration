import json
from datetime import timedelta

import boto3
from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone

from common.models import OutboxEvent


def _eventbridge_client():
    return boto3.client("events", region_name=settings.AWS_REGION)


def _build_entries(events, event_bus_name: str):
    entries = []
    for event in events:
        payload = event.payload or {}
        entries.append(
            {
                "EventBusName": event_bus_name,
                "Source": payload.get("source", "stagelog.core"),
                "DetailType": event.event_type,
                "Detail": json.dumps(payload, ensure_ascii=False),
            }
        )
    return entries


def publish_outbox_batch(
    *,
    database: str = "default",
    aggregate_type: str = "notification",
    limit: int = 50,
    max_retries: int = 5,
    retry_base_delay_seconds: int = 30,
):
    now = timezone.now()
    manager = OutboxEvent.objects.using(database)
    qs = manager.filter(status=OutboxEvent.Status.PENDING, available_at__lte=now)
    if aggregate_type:
        qs = qs.filter(aggregate_type=aggregate_type)

    with transaction.atomic(using=database):
        try:
            events = list(qs.select_for_update(skip_locked=True).order_by("outbox_id")[:limit])
        except DatabaseError:
            events = list(qs.select_for_update().order_by("outbox_id")[:limit])

        if not events:
            return {"picked": 0, "published": 0, "failed": 0}

        entries = _build_entries(events, settings.NOTIFICATION_EVENT_BUS_NAME)

        try:
            response = _eventbridge_client().put_events(Entries=entries)
            result_entries = response.get("Entries", [])
        except Exception:
            result_entries = [{} for _ in events]

        published = 0
        failed = 0
        for idx, event in enumerate(events):
            result = result_entries[idx] if idx < len(result_entries) else {}
            if result.get("EventId") and not result.get("ErrorCode"):
                event.status = OutboxEvent.Status.PUBLISHED
                event.published_at = now
                event.save(using=database, update_fields=["status", "published_at"])
                published += 1
                continue

            failed += 1
            event.attempts += 1
            if event.attempts >= max_retries:
                event.status = OutboxEvent.Status.FAILED
                event.save(using=database, update_fields=["status", "attempts"])
                continue

            event.status = OutboxEvent.Status.PENDING
            event.available_at = now + timedelta(seconds=retry_base_delay_seconds * event.attempts)
            event.save(using=database, update_fields=["status", "attempts", "available_at"])

        return {"picked": len(events), "published": published, "failed": failed}
