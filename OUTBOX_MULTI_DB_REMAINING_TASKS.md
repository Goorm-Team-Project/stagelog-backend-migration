# Outbox Multi-DB Remaining Tasks (Non-Backend)

아래 항목은 백엔드 코드 외 작업(인프라/배포/운영)이다.

## 1) DB 마이그레이션 실행

`common.OutboxEvent` 테이블을 3개 DB alias에 모두 생성해야 한다.

```bash
python manage.py migrate --database=default
python manage.py migrate --database=auth_db
python manage.py migrate --database=events_db
```

검증:
- `stagelog_core.outbox_events`
- `stagelog_auth.outbox_events`
- `stagelog_events.outbox_events`


## 2) Outbox 워커 실행 커맨드 전환

현재 단일 DB 커맨드(`publish_outbox_notifications`) 대신, 멀티 DB 커맨드 사용:

```bash
python manage.py publish_outbox_all_databases \
  --databases="${OUTBOX_DATABASES:-default,auth_db,events_db}" \
  --limit="${OUTBOX_PUBLISH_BATCH_SIZE:-50}" \
  --max-retries="${OUTBOX_MAX_RETRIES:-5}" \
  --retry-base-delay-seconds="${OUTBOX_RETRY_BASE_DELAY_SECONDS:-30}"
```

## 3) K8s 매니페스트 정리

- `outbox-worker` Deployment는 1개만 유지
- `outbox-worker-auth` 같은 분리 배포는 제거/비활성
- env에 `OUTBOX_DATABASES=default,auth_db,events_db` 주입


## 4) SSM/Secret 주입 확인

`outbox-worker`에 아래 키가 모두 주입되는지 확인:
- `DB_NAME_CORE`, `DB_USER_CORE`, `DB_PASSWORD_CORE`
- `DB_NAME_AUTH`, `DB_USER_AUTH`, `DB_PASSWORD_AUTH`
- `DB_NAME_EVENTS`, `DB_USER_EVENTS`, `DB_PASSWORD_EVENTS`
- `OUTBOX_DATABASES`


## 5) 운영 검증 시나리오

1. Core 경로에서 알림 발생 -> `default.outbox_events` 적재
2. Auth(레벨업) 경로에서 알림 발생 -> `auth_db.outbox_events` 적재
3. Events 경로 알림(추가 시) -> `events_db.outbox_events` 적재
4. 단일 outbox 워커가 3개 DB를 모두 publish 처리
5. EventBridge -> SQS -> DynamoDB 반영 확인
