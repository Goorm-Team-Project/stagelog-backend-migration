from typing import Optional
from django.contrib.auth import get_user_model

from common.models import OutboxEvent
from posts.models import Post
from events.models import Event

User = get_user_model()

def create_notification(
    user: User,
    type: str,
    message: str,
    relate_url: Optional[str] = None,
    post: Optional[Post] = None,
    event: Optional[Event] = None,
):
    """
    알림 엔티티를 직접 저장하지 않고 outbox 이벤트를 적재한다.
    워커가 outbox_events -> EventBridge/SQS -> Notification 서비스로 전달한다.
    """
    try:
        payload = {
            "recipient_user_id": user.user_id,
            "type": type,
            "message": message,
            "relate_url": relate_url,
            "post_id": getattr(post, "post_id", None),
            "event_id": getattr(event, "event_id", None),
        }

        OutboxEvent.objects.create(
            aggregate_type="notification",
            aggregate_id=str(user.user_id),
            event_type="notification.requested",
            payload=payload,
        )
    except Exception as e:
        print(f"알림 생성 실패: {e}")
