# EKS Base + MSA Porting Plan

## 목표
- `feature/eks`를 인프라 베이스로 유지한다.
- `feature/msa`에서 작성한 API Gateway/Auth/Notification/Redis 구성을 EKS 구조에 맞게 포팅한다.
- 최종적으로 MSA 기능이 EKS 기반에서 정상 동작하도록 정합성을 맞춘다.

## 1. 기준 계약 고정 (Remote State Outputs)
- `2-ephemeral`에서 외부에 제공할 output 계약을 먼저 고정한다.
- 최소 필수 항목:
  - `cluster_name`
  - `oidc_provider_arn`
  - `oidc_provider_url`
  - `ingress_lb_dns` 또는 `ingress_lb_arn`
- `1-permanent`는 위 output을 `terraform_remote_state`로 소비하도록 통일한다.

## 2. API 진입 구조 확정
- 권장 구조:
  - `CloudFront -> API Gateway -> (VPC Link) -> EKS Ingress ALB`
- 대안:
  - `CloudFront -> EKS Ingress` 직결
- 구조 확정 후 API Gateway 필요 범위와 인증 경로를 확정한다.

## 3. API Gateway 모듈 재도입 (EKS 호환)
- `feature/msa`의 `api-gateway*.tf`를 기반으로 재작성한다.
- `core_integration`의 대상은 EC2 ALB 가정 대신 EKS ingress 기준으로 교체한다.
- 공개/보호 route 분기(Authorizer 적용 정책)는 기존 규칙을 유지한다.

## 4. Auth Lambda / Authorizer 정렬
- `auth-lambda.tf`를 EKS 베이스 환경에 맞춰 복원/정리한다.
- `aws_lambda_permission`과 API Gateway route authorizer 연결을 재검증한다.
- stage, custom domain, access log 설정을 운영 값 기준으로 고정한다.

## 5. Notification 인프라 재도입
- `notification-infra.tf`를 EKS 베이스에 맞게 재도입한다.
- 포함 리소스:
  - EventBridge bus/rule/target
  - SQS + DLQ + queue policy
  - DynamoDB
- detail-type은 백엔드 이벤트 매핑과 1:1로 유지한다.

## 6. Redis 재도입
- `redis.tf`를 재도입하고 EKS 워커/앱 접근 가능하도록 네트워크를 정리한다.
- 공용 사용 시 키/TTL 정책을 문서화한다.
  - 예: auth 블랙리스트, notification dedupe/unread

## 7. IAM / IRSA 통합
- `feature/eks` IAM 체계를 유지한 채 MSA 권한을 추가한다.
- ServiceAccount별 최소권한 분리:
  - Outbox publisher: `events:PutEvents`
  - Notification consumer: `sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes`, `dynamodb:PutItem`
  - 필요 시 S3 presign 권한 분리
- 정적 access key 사용은 최소화하고 IRSA를 기본으로 한다.

## 8. SG / VPC 네트워크 정합성
- EKS private subnet, DB private subnet 구조 기준으로 경로를 재검증한다.
- 확인 경로:
  - API Gateway VPC Link ENI -> ingress ALB
  - ingress ALB -> EKS workload
  - EKS workload -> RDS/Redis

## 9. Variables / Outputs 표준화
- `1-permanent`, `2-ephemeral`의 변수/출력명을 통일한다.
- 레거시 output은 제거하거나 호환 alias를 제공한다.
- 하위 모듈/브랜치 참조가 깨지지 않도록 계약 문서화한다.

## 10. 적용 순서 (실행 계획)
- 1단계: `2-ephemeral` apply (EKS/ingress 기반 output 생성)
- 2단계: `1-permanent` apply (API Gateway/Auth/Notification/Redis)
- 3단계: 기능 검증
  - `/api/auth/*` 라우팅 및 authorizer
  - 공개/보호 API 분기
  - `outbox -> eventbridge -> sqs -> dynamodb`
  - Redis 연동(auth/notification)

## 완료 기준
- EKS 기반에서 API 라우팅, 인증, 알림 파이프라인, Redis 연동이 모두 정상 동작한다.
- 브랜치 간 output/변수 계약이 고정되어 추가 충돌 없이 확장 가능하다.
