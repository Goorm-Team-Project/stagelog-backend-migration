# apps/bookmarks/views.py

import json

from django.views.decorators.http import require_http_methods, require_safe
from apps.common.utils import common_response, login_check
from common.services import internal_api
from bookmarks.models import Bookmark
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Count


def _event_exists(event_id: int) -> bool:
    return internal_api.event_exists(event_id)


def _get_events_batch(event_ids):
    return internal_api.get_events_batch(event_ids)


def _event_start_date_sort_key(event_row):
    value = event_row.get("start_date")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value or ""


@csrf_exempt
@require_http_methods(["POST"])
def internal_bookmark_favorite_count(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"message": "invalid json"}, status=400)

    raw_event_ids = payload.get("event_ids")
    if not isinstance(raw_event_ids, list):
        return JsonResponse({"message": "event_ids must be list"}, status=400)

    normalized_event_ids = []
    for raw in raw_event_ids:
        try:
            normalized_event_ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not normalized_event_ids:
        return JsonResponse({"counts": []}, status=200)

    favorite_rows = (
        Bookmark.objects.filter(event_id__in=normalized_event_ids)
        .values("event_id")
        .annotate(favorite_count=Count("event_id"))
    )
    favorite_count_map = {int(row["event_id"]): int(row["favorite_count"]) for row in favorite_rows}

    counts = []
    seen = set()
    for event_id in normalized_event_ids:
        if event_id in seen:
            continue
        seen.add(event_id)
        counts.append(
            {
                "event_id": int(event_id),
                "favorite_count": favorite_count_map.get(int(event_id), 0),
            }
        )

    return JsonResponse({"counts": counts}, status=200)


@csrf_exempt
@require_http_methods(["POST"]) # POST만 허용
@login_check # 토큰 검증 필수
def toggle_bookmark(request, event_id):
    try:
        user_id = request.user_id

        # 공연 존재 여부는 events 서비스 DB에서 확인
        if not _event_exists(event_id):
            return common_response(False, message="존재하지 않는 공연입니다.", status=404)

        # 2. 토글 로직 (있으면 삭제, 없으면 생성)
        bookmark = Bookmark.objects.filter(user_id=user_id, event_id=event_id).first()

        if bookmark:
            bookmark.delete()
            return common_response(True, message="북마크 취소됨", data={"state": "off"}, status=200)
        else:
            Bookmark.objects.create(user_id=user_id, event_id=event_id)
            return common_response(True, message="북마크 성공!", data={"state": "on"}, status=201)

    except internal_api.InternalApiError:
        return common_response(False, message="내부 API 호출 실패", status=502)
    except Exception as e:
        print(f"Bookmark Error: {e}")
        return common_response(False, message="서버 에러 발생", status=500)

@require_safe
@login_check
def mypage(request):
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('size', 1))

        my_booked_ids = Bookmark.objects.filter(user_id=request.user_id)\
                                        .order_by('-created_at')\
                                        .values_list('event_id', flat=True)

        my_booked_ids = list(my_booked_ids)
        event_map = _get_events_batch(my_booked_ids)
        ordered_events = [event_map[eid] for eid in my_booked_ids if eid in event_map]
        ordered_events.sort(key=_event_start_date_sort_key, reverse=True)

        favorite_rows = (
            Bookmark.objects.filter(event_id__in=my_booked_ids)
            .values("event_id")
            .annotate(favorite_count=Count("event_id"))
        )
        favorite_count_map = {row["event_id"]: row["favorite_count"] for row in favorite_rows}

        paginator = Paginator(ordered_events, page_size)

        try:
            current_page_data = paginator.page(page)
        except EmptyPage:
            current_page_data = []

        event_list = []
        for event in current_page_data:
            event_id = event["event_id"] if isinstance(event, dict) else event.event_id
            title = event["title"] if isinstance(event, dict) else event.title
            artist = event.get("artist") if isinstance(event, dict) else (event.artist if hasattr(event, 'artist') else "")
            start_date = event.get("start_date") if isinstance(event, dict) else event.start_date
            end_date = event.get("end_date") if isinstance(event, dict) else event.end_date
            venue = event.get("venue") if isinstance(event, dict) else event.venue
            poster = event.get("poster") if isinstance(event, dict) else event.poster

            event_list.append({
                "event_id": event_id,
                "title": title,
                "artist": artist or "",
                "start_date": start_date.strftime('%Y-%m-%d') if hasattr(start_date, "strftime") and start_date else start_date,
                "end_date": end_date.strftime('%Y-%m-%d') if hasattr(end_date, "strftime") and end_date else end_date,
                "venue": venue,
                "poster": poster if poster else None,
                "favorite_count": favorite_count_map.get(event_id, 0),
            })

        return common_response(
            success=True,
            message="즐겨찾기 목록 조회 성공",
            data={
                "events": event_list,
                "has_next": current_page_data.has_next() if hasattr(current_page_data, 'has_next') else False,
                "total_count": paginator.count,
                "total_pages": paginator.num_pages,
            },
            status=200
        )
        
    except internal_api.InternalApiError:
        return common_response(success=False, message="내부 API 호출 실패", status=502)
    except Exception as e:
        print(f"[ERROR] mypage: {e}") 
        return common_response(success=False, message="서버 에러", status=500)
    
