# EKS Handoff: Internal API Routing & Namespace Guide

## 1) Namespace 정책 (현재 권장안)

- 지금 단계에서는 도메인별(`auth/events/core`) namespace 분리 필수 아님
- 우선 **환경 단위 namespace 1개**로 시작
  - 예: `dev` 또는 `stagelog`
- 추후 필요 시 도메인 분리 고려
  - 권한/배포 독립 요구가 커질 때만 분리


## 2) 서비스 간 통신 원칙

- 서비스 간 내부 호출은 **API Gateway/외부 ALB 경유 금지**
- Kubernetes 내부 DNS + ClusterIP Service 사용
- 내부 API 경로는 `/internal/*` 전용
- `/internal/*`는 외부에 노출하지 않음

예시(같은 namespace):
- `http://auth-svc:8000/internal/users:batch-get`
- `http://events-svc:8000/internal/events:batch-summary`
- `http://core-svc:8000/internal/bookmarks/events:favorite-count`

예시(FQDN):
- `http://auth-svc.<namespace>.svc.cluster.local:8000/...`


## 3) 외부 노출 경계

- 외부 공개 경로: `/api/*`
- 내부 전용 경로: `/internal/*` (Ingress/API Gateway 라우트에 추가 금지)


## 4) EKS 팀에 필요한 설정

1. Service 생성
- `auth-svc`
- `events-svc`
- `core-svc`

2. 앱 환경변수 주입
- `AUTH_INTERNAL_BASE_URL`
- `EVENTS_INTERNAL_BASE_URL`
- `CORE_INTERNAL_BASE_URL`

권장 기본값:
- `http://auth-svc:8000`
- `http://events-svc:8000`
- `http://core-svc:8000`

3. 네트워크 정책(선택 -> 권장)
- NetworkPolicy로 서비스 간 허용 트래픽만 열기


## 5) 내부 API 목록 (구현 대상)

상세는 아래 문서 참고:
- `INTERNAL_API_CANDIDATES.md`

핵심 목록:
- `POST /internal/users:batch-get`
- `POST /internal/users/{user_id}/exp`
- `GET /internal/events/{event_id}/exists`
- `GET /internal/events/{event_id}/summary`
- `POST /internal/events:batch-summary`
- `POST /internal/bookmarks/events:favorite-count`


## 6) 최종 목표

- 교차 DB 직접 조회 제거
- 서비스 간 데이터 참조는 내부 API(또는 이벤트/리드모델)로만 처리
- 이후 DB 물리 분리 시에도 코드 변경 최소화
