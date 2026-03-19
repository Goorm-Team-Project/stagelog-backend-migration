# Notifications

StageLog의 알림 시스템은 더 이상 RDS `notifications` 테이블을 중심으로 동작하지 않습니다.  
현재 기준의 중심 저장소는 **DynamoDB**이고, 알림 생성은 **Outbox -> EventBridge -> SQS -> Consumer -> DynamoDB** 흐름으로 처리합니다.

이 문서는 `notifications` 도메인의 **현재 로직**과 **의도된 인프라 설계**를 함께 정리합니다.

---

## 1) 현재 목표

- 알림 생성은 본 요청 처리와 분리한다
- 알림 조회/읽음은 DynamoDB에서 직접 처리한다
- 알림 생성 실패가 사용자 핵심 요청을 깨지 않게 한다
- 중복 소비는 DynamoDB 조건식으로 막고, 저장소는 DynamoDB를 source of truth로 둔다

---

## 2) 구성 요소

### 2-1. API 서버
- `GET /api/notifications`
- `GET /api/notifications/check`
- `PATCH /api/notifications/<notification_id>/read`

구현 파일
- [views.py](/home/woosupar/stagelog-backend-migration/apps/notifications/views.py)
- [store.py](/home/woosupar/stagelog-backend-migration/apps/notifications/store.py)

### 2-2. 알림 생성자
도메인 코드에서 알림을 직접 저장하지 않고 Outbox 이벤트를 적재합니다.

구현 파일
- [services.py](/home/woosupar/stagelog-backend-migration/apps/notifications/services.py)

### 2-3. Outbox Worker
여러 DB(`default`, `auth_db`, `events_db`)의 `OutboxEvent`를 읽어 EventBridge로 발행합니다.

구현 파일
- [publish_outbox_all_databases.py](/home/woosupar/stagelog-backend-migration/apps/common/management/commands/publish_outbox_all_databases.py)
- [outbox_publisher.py](/home/woosupar/stagelog-backend-migration/apps/common/services/outbox_publisher.py)

### 2-4. Notification Consumer
SQS에서 메시지를 받아 DynamoDB에 실제 알림 아이템을 저장합니다.

구현 파일
- [consume_notification_queue.py](/home/woosupar/stagelog-backend-migration/apps/notifications/management/commands/consume_notification_queue.py)
- [services_consumer.py](/home/woosupar/stagelog-backend-migration/apps/notifications/services_consumer.py)

---

## 3) 전체 흐름

### 3-1. 알림 생성
1. `posts`, `events`, `users` 등 도메인 코드가 `create_notification(...)` 호출
2. `notifications.services.create_notification()`가 `OutboxEvent` 생성
3. Outbox Worker가 pending outbox를 읽음
4. EventBridge로 이벤트 발행
5. EventBridge 규칙이 SQS로 전달
6. Notification Consumer가 SQS 메시지를 읽음
7. Consumer가 DynamoDB에 알림 저장
8. 이후 API 서버가 DynamoDB에서 조회/읽음 처리

### 3-2. 알림 조회
1. 클라이언트가 `/api/notifications` 호출
2. API 서버가 DynamoDB `gsi1`로 사용자 알림을 최신순 조회
3. 응답 페이로드 반환

### 3-3. 안 읽은 개수 조회
1. 클라이언트가 `/api/notifications/check` 호출
2. API 서버가 사용자별 카운트 메타 아이템을 한 번 조회
3. unread count 반환

### 3-4. 읽음 처리
1. 클라이언트가 `/api/notifications/{notification_id}/read` 호출
2. API 서버가 `pk/sk`로 알림 1건 조회
3. `is_read=false -> true`로 변경
4. 같은 사용자 메타 아이템의 `unread_count` 감소

---

## 4) DynamoDB 설계

현재 코드가 전제로 하는 알림 저장 구조는 아래와 같습니다.

### 4-1. 알림 아이템
```json
{
  "pk": "USER#1",
  "sk": "NOTI#123456789012345",
  "gsi1pk": "USER#1",
  "gsi1sk": "TS#2026-03-19T12:34:56+09:00#123456789012345",
  "notification_id": 123456789012345,
  "event_id": "8db0d5f9-...",
  "recipient_user_id": 1,
  "type": "comment",
  "message": "새 댓글이 달렸습니다.",
  "relate_url": "/posts/10",
  "post_id": 10,
  "related_event_id": 4104,
  "is_read": false,
  "created_at": "2026-03-19T12:34:56+09:00",
  "ttl": 1773891296
}
```

### 4-2. 사용자 메타 카운트 아이템
```json
{
  "pk": "USER#1",
  "sk": "META#COUNTS",
  "unread_count": 7,
  "updated_at": "2026-03-19T12:35:10+09:00"
}
```

### 4-3. 키 설계 의도
- `pk = USER#{user_id}`
  - 사용자 단위 파티셔닝
- `sk = NOTI#{notification_id}`
  - 읽음 처리 시 알림 1건을 바로 찾기 위함
- `gsi1pk = USER#{user_id}`
- `gsi1sk = TS#{created_at}#{notification_id}`
  - 목록 조회를 최신순으로 만들기 위함
- `META#COUNTS`
  - unread count를 전체 스캔 없이 한 번에 읽기 위함

### 4-4. 현재 필요한 테이블 리소스
현재 live 테이블 `stagelog-notifications`는 아래 리소스만 있으면 충분합니다.

- Primary Key
  - `pk` (HASH)
  - `sk` (RANGE)
- GSI1
  - `gsi1pk` (HASH)
  - `gsi1sk` (RANGE)

현재 live 테이블은 이 구조를 이미 만족하며, 아이템 수는 `0`입니다.

---

## 5) RDS 구조와 차이

기존 RDS 모델
- [models.py](/home/woosupar/stagelog-backend-migration/apps/notifications/models.py)

기존 RDS는 `notification_id`가 실제 PK인 정규화 테이블이었습니다.

현재 DynamoDB는 다릅니다.
- 알림 1건 중심이 아니라, **사용자 inbox 중심**
- `notification_id`는 실제 item key 일부로 승격
- unread count는 별도 메타 아이템으로 분리
- 조회와 읽음 성능을 위해 키를 설계함

즉:
- RDS: 행 중심
- DynamoDB: 사용자별 알림 피드 중심

---

## 6) Consumer 중복 처리 정책

현재 consumer는 Redis dedupe를 사용하지 않습니다.

이유
- Redis에 먼저 dedupe 키를 찍고, 그 뒤 DynamoDB 저장이 실패하면 알림 유실 위험이 있음
- 중복 여부는 **실제 저장 성공 여부**와 묶여 있어야 안전함

현재 정책
1. DynamoDB `put_item(... ConditionExpression=attribute_not_exists(pk) AND attribute_not_exists(sk))`
2. 성공 시 새 알림
3. `ConditionalCheckFailedException`이면 중복으로 간주
4. 중복 메시지는 delete
5. 기타 실패는 재시도/DLQ 대상

즉, dedupe의 source of truth도 DynamoDB입니다.

---

## 7) Outbox 설계

알림 생성은 동기 요청의 부가효과입니다.  
따라서 핵심 요청 경로에서 직접 DynamoDB에 쓰지 않고 Outbox를 거칩니다.

장점
- 본 요청(latency)와 알림 적재를 분리 가능
- 실패 시 재시도 가능
- 여러 DB에서 생성된 알림 이벤트를 한 파이프라인으로 통합 가능

관련 설정
- `OUTBOX_DATABASES`
- `OUTBOX_PUBLISH_BATCH_SIZE`
- `OUTBOX_MAX_RETRIES`
- `OUTBOX_RETRY_BASE_DELAY_SECONDS`
- `OUTBOX_NOTIFICATION_AGGREGATE_TYPE`

관련 파일
- [publish_outbox_all_databases.py](/home/woosupar/stagelog-backend-migration/apps/common/management/commands/publish_outbox_all_databases.py)
- [outbox_publisher.py](/home/woosupar/stagelog-backend-migration/apps/common/services/outbox_publisher.py)

---

## 8) 워커 프로세스 모델

알림 관련 워커는 Gunicorn HTTP 서버가 아닙니다.  
둘 다 **Django management command를 실행하는 long-running worker 프로세스**입니다.

### Outbox Worker
```bash
python manage.py publish_outbox_all_databases
```

### Notification Consumer
```bash
python manage.py consume_notification_queue
```

즉:
- API 서버: `gunicorn config.wsgi:application`
- 워커: `python manage.py ...`

---

## 9) 로깅

### 9-1. Outbox Publisher 로그
현재 아래 로그를 남깁니다.
- `batch_start`
- `batch_end`
- `published`
- `publish_failed`
- `put_events_failed`

구현 파일
- [outbox_publisher.py](/home/woosupar/stagelog-backend-migration/apps/common/services/outbox_publisher.py)

### 9-2. Notification Consumer 로그
현재 아래 로그를 남깁니다.
- `batch_start`
- `saved`
- `duplicate`
- `client_error`
- `failed`
- `batch_end`

구현 파일
- [services_consumer.py](/home/woosupar/stagelog-backend-migration/apps/notifications/services_consumer.py)

운영에서는 이 로그만으로도
- 어떤 이벤트가 발행됐는지
- 어떤 메시지가 중복인지
- 어느 단계에서 실패했는지
대부분 추적 가능합니다.

---

## 10) 환경 변수

현재 notifications 흐름에서 중요한 설정은 아래와 같습니다.

```env
AWS_REGION=ap-northeast-2
NOTIFICATION_EVENT_BUS_NAME=stagelog-notification-bus
NOTIFICATION_SQS_QUEUE_URL=...
NOTIFICATION_DDB_TABLE_NAME=stagelog-notifications
NOTIFICATION_CONSUMER_MAX_MESSAGES=10
NOTIFICATION_CONSUMER_WAIT_TIME_SECONDS=20
NOTIFICATION_DDB_TTL_DAYS=30
OUTBOX_PUBLISH_BATCH_SIZE=50
OUTBOX_MAX_RETRIES=5
OUTBOX_RETRY_BASE_DELAY_SECONDS=30
OUTBOX_NOTIFICATION_AGGREGATE_TYPE=notification
OUTBOX_DATABASES=default,auth_db,events_db
```

참고
- `NOTIFICATION_DEDUPE_TTL_SECONDS`
- `NOTIFICATION_UNREAD_CACHE_TTL_SECONDS`

이 두 설정은 과거 Redis 기반 dedupe/unread cache에서 쓰던 값이라,  
현재 코드 기준으로는 핵심 동작에 필요하지 않습니다. 정리 대상입니다.

---

## 11) 현재 인프라 의도

알림 시스템은 최종적으로 아래처럼 분리 운영하는 것을 목표로 합니다.

### 11-1. 외부 API
- `notifications-svc`
  - `/api/notifications`
  - `/api/notifications/check`
  - `/api/notifications/{id}/read`

### 11-2. 비동기 워커
- `outbox-worker`
  - 여러 DB의 outbox 발행 전용
- `notification-consumer`
  - SQS -> DynamoDB 적재 전용

### 11-3. 저장소
- DynamoDB
  - 알림 본문
  - unread count 메타
- EventBridge
  - 도메인 이벤트 전달
- SQS
  - consumer decoupling / retry / DLQ

현재 백엔드 코드 기준으로는 이 구조를 지원할 준비가 되어 있고,  
배포 매니페스트와 서비스 분리는 별도 단계에서 정리하면 됩니다.

---

## 12) 남은 과제

1. `notifications-svc` 외부 라우팅 분리
2. `outbox-worker`, `notification-consumer` 전용 배포 정리
3. DynamoDB TTL/운영 모니터링 정비
4. 알림 타입별 payload 규약 정리
5. 기존 `Notification` RDS 모델 제거 시점 결정

---

## 13) 한 줄 결론

현재 알림 시스템은

- 생성: **Outbox -> EventBridge -> SQS -> Consumer**
- 저장: **DynamoDB**
- 조회/읽음: **DynamoDB 직접 처리**
- 중복 처리: **DynamoDB 조건식**

으로 설계되어 있습니다.

즉, 알림은 이제 관계형 CRUD보다 **비동기 이벤트 기반 inbox 시스템**으로 보는 것이 맞습니다.
