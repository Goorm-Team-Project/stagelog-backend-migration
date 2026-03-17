# Deploy Verification Checklist

## 1) DB Migration
- `python manage.py migrate --database=default`
- `python manage.py migrate --database=auth_db`
- `python manage.py migrate --database=events_db`

## 2) Outbox Worker
- worker/apply:
  - `kubectl apply -f deploy/k8s/outbox-worker-deployment.yaml`
- 상태 확인:
  - `kubectl get deploy,pods | rg outbox-worker`
  - `kubectl logs deploy/stagelog-outbox-worker --tail=100`

## 3) Notification Consumer
- `kubectl apply -f deploy/k8s/notification-consumer-deployment.yaml`
- `kubectl apply -f deploy/k8s/notification-consumer-scaledobject.yaml`
- 상태 확인:
  - `kubectl get deploy,pods,scaledobject | rg notification-consumer`
  - `kubectl logs deploy/stagelog-notification-consumer --tail=100`

## 4) End-to-End (알림)
- 댓글/좋아요/레벨업 트리거 API 호출
- core/auth DB `outbox_events`에 `pending -> published` 전환 확인
- SQS queue depth 증가 후 감소 확인
- DynamoDB `stagelog-notifications`에 신규 item 생성 확인

## 5) Failure Path
- Consumer 권한/테이블명을 임시로 잘못 설정해 실패 유도
- 실패 시 SQS delete가 안 되고 재시도되는지 확인
- 최대 재시도 후 DLQ 적재되는지 확인

## 6) Redis
- `noti:dedupe:event:*` 키 생성 확인
- `noti:unread:<user_id>` 카운트 증가 확인
- (AutoBan 사용 시) `block_<ip>`, `req_count_<ip>` 공유 확인
