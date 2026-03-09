# TODO

- [ ] 멀티 DB 마이그레이션 실행
  - `python manage.py migrate --database=default`
  - `python manage.py migrate --database=auth_db`
  - `python manage.py migrate --database=events_db`

- [ ] EKS 구성 후 Outbox Worker Deployment 적용
  - `deploy/k8s/outbox-worker-deployment.yaml`의 `image`, `serviceAccountName`, `secretRef` 실제 값으로 치환
  - `deploy/k8s/outbox-worker-auth-deployment.yaml`의 `image`, `serviceAccountName`, `secretRef` 실제 값으로 치환
  - 워커 ServiceAccount에 EventBridge `events:PutEvents` 권한(IRSA/Role) 연결
  - `kubectl apply -f deploy/k8s/outbox-worker-deployment.yaml`
  - `kubectl apply -f deploy/k8s/outbox-worker-auth-deployment.yaml`
  - 워커 로그/상태 확인 (`kubectl logs`, `kubectl get pods`)으로 outbox 발행 검증

- [ ] Notification Consumer(SQS -> DynamoDB) 배포
  - `deploy/k8s/notification-consumer-deployment.yaml`의 `image`, `serviceAccountName`, `secretRef` 실제 값으로 치환
  - `deploy/k8s/notification-consumer-scaledobject.yaml`의 `queueURL` 실제 값으로 치환
  - 워커 ServiceAccount에 SQS(`ReceiveMessage`,`DeleteMessage`,`GetQueueAttributes`) + DynamoDB(`PutItem`) 권한(IRSA/Role) 연결
  - `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL` 시크릿 반영
  - Redis 연결 성공 여부 및 dedupe 키(`noti:dedupe:event:*`) 생성 확인
  - `kubectl apply -f deploy/k8s/notification-consumer-deployment.yaml`
  - `kubectl apply -f deploy/k8s/notification-consumer-scaledobject.yaml`

- [ ] AutoBan(IP 필터링) Redis 공유 연결
  - API 파드 시크릿에 `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_SSL` 반영
  - API 파드 시크릿에 `AUTO_BAN_ENABLED`, `AUTO_BAN_LIMIT_WINDOW_SECONDS`, `AUTO_BAN_MAX_REQUESTS`, `AUTO_BAN_BLOCK_TIME_SECONDS` 반영
  - API Deployment 롤링 재시작 후 `common.middleware.AutoBanMiddleware` 활성화 확인
  - 여러 파드에서 동일 IP 차단 상태 공유되는지 확인 (`block_<ip>`, `req_count_<ip>` 키)
