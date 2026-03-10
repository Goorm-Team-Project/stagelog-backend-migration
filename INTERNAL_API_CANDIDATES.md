# Internal API Candidates (DB Cross-Read Replacement)

목적: 현재 `posts/bookmarks/events`에서 발생하는 교차 DB 직접 조회를 서비스 간 API 호출로 대체한다.

## 1) Posts -> Users

### 1-1. 유저 닉네임 배치 조회
- Method/Path: `POST /internal/users:batch-get`
- Request:
```json
{
  "user_ids": [1, 2, 3]
}
```
- Response:
```json
{
  "users": [
    { "user_id": 1, "nickname": "alice" },
    { "user_id": 2, "nickname": "bob" }
  ]
}
```
- 대체 대상 코드:
  - `apps/posts/views.py`의 `_get_user_nickname_map`
  - `posts_list`, `event_posts_list`, `post_detail`, `comment_create` 등 닉네임 조합 구간

### 1-2. 유저 경험치 적용
- Method/Path: `POST /internal/users/{user_id}/exp`
- Request:
```json
{
  "policy": "POST"
}
```
- Response:
```json
{
  "success": true,
  "level_up": false,
  "current_level": 3,
  "gained_exp": 10
}
```
- 대체 대상 코드:
  - `apps/posts/views.py`의 `User.objects.get(...) + apply_user_exp(...)`


## 2) Posts/Bookmarks -> Events

### 2-1. 이벤트 존재 여부 확인
- Method/Path: `GET /internal/events/{event_id}/exists`
- Response:
```json
{
  "exists": true
}
```
- 대체 대상 코드:
  - `apps/posts/views.py`의 `Event.objects.filter(...).exists()`
  - `apps/bookmarks/views.py`의 `Event.objects.filter(...).exists()`

### 2-2. 이벤트 단건 메타 조회
- Method/Path: `GET /internal/events/{event_id}/summary`
- Response:
```json
{
  "event_id": 10,
  "title": "공연명",
  "poster": "https://...",
  "artist": "아티스트",
  "start_date": "2026-03-01",
  "end_date": "2026-03-02",
  "group_name": "그룹"
}
```
- 대체 대상 코드:
  - `apps/posts/views.py`의 `Event.objects.get(event_id=...)`
  - `event_posts_list` 상단 event_meta 구성

### 2-3. 이벤트 배치 조회 (목록 조합용)
- Method/Path: `POST /internal/events:batch-summary`
- Request:
```json
{
  "event_ids": [10, 20, 30]
}
```
- Response:
```json
{
  "events": [
    { "event_id": 10, "title": "A", "poster": "https://..." },
    { "event_id": 20, "title": "B", "poster": "https://..." }
  ]
}
```
- 대체 대상 코드:
  - `apps/posts/views.py`의 `_get_event_map`
  - `apps/bookmarks/views.py`의 `mypage` 이벤트 목록 조회


## 3) Events -> Core(Bookmarks)

### 3-1. 이벤트별 즐겨찾기 수 배치 조회
- Method/Path: `POST /internal/bookmarks/events:favorite-count`
- Request:
```json
{
  "event_ids": [10, 20, 30]
}
```
- Response:
```json
{
  "counts": [
    { "event_id": 10, "favorite_count": 120 },
    { "event_id": 20, "favorite_count": 35 }
  ]
}
```
- 대체 대상 코드:
  - `apps/events/views.py`의 `Count("bookmarks")` 결합 구간


## 4) 우선순위

1. `users:batch-get`, `events:batch-summary`, `events/{id}/exists`
2. `users/{id}/exp`
3. `bookmarks/events:favorite-count`


## 5) 공통 규칙(권장)

- Path prefix: `/internal/*` (외부 공개 API와 분리)
- 인증: 서비스 간 호출 전용 토큰(mTLS 또는 내부 JWT)
- 타임아웃: connect 300ms / read 700ms (초기값)
- 실패 처리:
  - 목록 보강 API 실패 시 기본값(`nickname=null`, `event=null`)로 degrade
  - 생성/검증 API 실패 시 명확한 4xx/5xx 반환
