# TODO

- [ ] 멀티 DB 마이그레이션 실행
  - `python manage.py migrate --database=default`
  - `python manage.py migrate --database=auth_db`
  - `python manage.py migrate --database=events_db`

- [ ] EKS 구성 후 Outbox Worker Deployment 적용
  - `deploy/k8s/outbox-worker-deployment.yaml`의 `image`, `serviceAccountName`, `secretRef` 실제 값으로 치환
  - 워커 ServiceAccount에 EventBridge `events:PutEvents` 권한(IRSA/Role) 연결
  - `kubectl apply -f deploy/k8s/outbox-worker-deployment.yaml`
  - 워커 로그/상태 확인 (`kubectl logs`, `kubectl get pods`)으로 outbox 발행 검증
