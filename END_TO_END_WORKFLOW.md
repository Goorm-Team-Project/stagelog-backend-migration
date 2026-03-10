# End-to-End Workflow (CloudFront + API Gateway + ALB/EKS + Notification Pipeline)

1. 사용자가 `pearlinvest.click` 접속
2. `CloudFront`가 경로 분기
   - 정적 리소스(`/*`) -> `S3`
   - API(`\/api/*`) -> `API Gateway`
3. API Gateway 라우팅
   - `/api/auth/*` -> Auth Lambda
   - 나머지 core API -> `VPC Link`
4. VPC Link가 VPC 내부 엔드포인트로 연결
5. VPC 내부의 `ALB(Ingress ALB)`가 요청 수신
6. ALB Listener/Rule이 경로 기준으로 EKS 서비스 Target Group으로 포워딩
7. EKS(NodeGroup) 위의 Ingress/Service가 트래픽을 해당 API Pod로 전달
8. Pod가 비즈니스 처리 후 RDS/Redis/S3 등 백엔드 리소스 접근
9. 알림 이벤트 발생 시 core DB outbox에 적재
10. Outbox Publisher(EKS 워커)가 EventBridge로 발행
11. EventBridge가 Rule 매칭 후 SQS로 전달
12. Notification Consumer(EKS 워커, KEDA 스케일)가 SQS 소비 후 DynamoDB 저장
13. 클라이언트 알림 조회 시 Notification 저장소 응답
14. 실패 메시지는 SQS 재시도 후 DLQ로 격리, 운영 모니터링/재처리 수행
