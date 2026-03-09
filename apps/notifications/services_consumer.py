import json
from datetime import timedelta

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.utils import timezone


def _sqs_client():
    return boto3.client("sqs", region_name=settings.AWS_REGION)


def _notification_table():
    dynamodb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)
    return dynamodb.Table(settings.NOTIFICATION_DDB_TABLE_NAME)


def _parse_sqs_message_body(body: str) -> dict:
    """
    EventBridge -> SQS 표준 형태를 파싱한다.
    body 예시:
      {
        "version": "...",
        "id": "...",
        "detail-type": "...",
        "source": "...",
        "detail": { ... } 또는 "detail": "{...json...}"
      }
    """
    outer = json.loads(body or "{}")
    detail = outer.get("detail", {})
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except json.JSONDecodeError:
            detail = {}
    if not isinstance(detail, dict):
        detail = {}
    return detail


def _to_dynamodb_item(detail: dict) -> dict:
    now = timezone.now()
    occurred_at = detail.get("occurred_at") or now.isoformat()
    event_id = detail.get("event_id") or f"missing-{int(now.timestamp() * 1000)}"
    user_id = str(detail.get("recipient_user_id") or "unknown")
    ttl = int((now + timedelta(days=settings.NOTIFICATION_DDB_TTL_DAYS)).timestamp())

    return {
        "pk": f"USER#{user_id}",
        "sk": f"NOTI#{occurred_at}#{event_id}",
        "gsi1pk": f"USER#{user_id}",
        "gsi1sk": occurred_at,
        "event_id": event_id,
        "recipient_user_id": int(detail.get("recipient_user_id") or 0),
        "type": detail.get("type", "notice"),
        "message": detail.get("message", ""),
        "relate_url": detail.get("relate_url"),
        "post_id": detail.get("post_id"),
        "event_ref_id": detail.get("related_event_id"),
        "is_read": False,
        "created_at": occurred_at,
        "ttl": ttl,
    }


def consume_notification_batch(
    *,
    queue_url: str,
    max_messages: int = 10,
    wait_time_seconds: int = 20,
):
    if not queue_url:
        return {"received": 0, "saved": 0, "deleted": 0, "failed": 0, "reason": "empty_queue_url"}

    sqs = _sqs_client()
    table = _notification_table()

    receive_kwargs = {
        "QueueUrl": queue_url,
        "MaxNumberOfMessages": max(1, min(max_messages, 10)),
        "WaitTimeSeconds": max(0, min(wait_time_seconds, 20)),
    }

    response = sqs.receive_message(**receive_kwargs)
    messages = response.get("Messages", [])
    if not messages:
        return {"received": 0, "saved": 0, "deleted": 0, "failed": 0}

    saved = 0
    deleted = 0
    failed = 0

    for msg in messages:
        receipt_handle = msg.get("ReceiptHandle")
        try:
            detail = _parse_sqs_message_body(msg.get("Body", ""))
            item = _to_dynamodb_item(detail)
            table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
            )
            saved += 1

            if receipt_handle:
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                deleted += 1
        except (json.JSONDecodeError, BotoCoreError, ClientError, ValueError, TypeError):
            # 저장/파싱 실패 시 delete하지 않고 재시도 또는 DLQ로 이동시킨다.
            failed += 1
            continue

    return {"received": len(messages), "saved": saved, "deleted": deleted, "failed": failed}
