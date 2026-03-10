from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_GET

from common.utils import common_response
from common.services import internal_api
from .models import Event
from django.shortcuts import render

# Create your views here.
# Point: 검색/정렬/페이지네이션 최소 단위 기능 구현.

def _event_summary(e: Event) -> dict:
    return {
        "event_id": e.event_id,
        "kopis_id": e.kopis_id,
        "title": e.title,
        "artist": e.artist,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "venue": e.venue,
        "poster": e.poster,

        "group_name": e.group_name,

        # 즐겨찾기 갯수 포함 (없으면 0)
        ## Event 객체에 favorite_coute 속성이 있으면 값을 내리고 없으면 0 내림
        "favorite_count": int(getattr(e, "favorite_count", 0) or 0),
    }

def _event_detail(e: Event) -> dict:
    return {
        "event_id": e.event_id,
        "kopis_id": e.kopis_id,
        "title": e.title,
        "artist": e.artist,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "venue": e.venue,
        "area": e.area,
        "age": e.age,
        "poster": e.poster,
        "time": e.time,
        "price": e.price,
        "relate_url": e.relate_url,
        "host": e.host,
        "genre": e.genre,
        "update_date": e.update_date.isoformat() if e.update_date else None,
        "group_name": e.group_name,
    }

def _favorite_count_map(event_ids):
    if not event_ids:
        return {}
    try:
        return internal_api.get_favorite_counts(event_ids)
    except Exception:
        # Internal API 전환 전/장애 시 favorite_count는 0으로 degrade
        return {int(event_id): 0 for event_id in event_ids}


@require_GET
def event_list(request):
    search = (request.GET.get("search") or "").strip()
    # 기본 최신순
    sort = (request.GET.get("sort") or "latest").strip().lower()

    #page/size 기본값
    try:
        page = int(request.GET.get("page") or 1)
        size = int(request.GET.get("size") or 10)
    except ValueError:
        return common_response(False, message="page/size는 정수여야 합니다.", status=400)
    
    if page <= 0 or size <= 0 or size > 100:
        return common_response(False, message="page는 1 이상, size는 1~100 범위에 포함되어야 합니다.", status=400)
    
    qs = Event.objects.all()

    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(artist__icontains=search) |
            Q(venue__icontains=search)
        )

    # sort 표준값
    ## sort=latest(기본), sort=favorite, sort=update, sort=name +) 내부 alias: fav, popular
    if sort in ("favorite", "fav", "bookmark", "popular", "popularity"):
        events = list(qs)
        favorite_map = _favorite_count_map([e.event_id for e in events])
        events.sort(
            key=lambda e: (
                -(favorite_map.get(e.event_id, 0)),
                -(e.update_date.timestamp() if e.update_date else 0),
                -e.event_id,
            )
        )
        paginator = Paginator(events, size)
        page_obj = paginator.get_page(page)
        page_events = list(page_obj.object_list)
        page_fav_map = {e.event_id: favorite_map.get(e.event_id, 0) for e in page_events}
        for e in page_events:
            setattr(e, "favorite_count", int(page_fav_map.get(e.event_id, 0)))
    elif sort in ("latest", "recent"):
        qs = qs.order_by("-start_date", "-event_id")
        paginator = Paginator(qs, size)
        page_obj = paginator.get_page(page)
        page_events = list(page_obj.object_list)
        page_fav_map = _favorite_count_map([e.event_id for e in page_events])
        for e in page_events:
            setattr(e, "favorite_count", int(page_fav_map.get(e.event_id, 0)))
    elif sort in ("update",):
        qs = qs.order_by("-update_date", "-event_id")
        paginator = Paginator(qs, size)
        page_obj = paginator.get_page(page)
        page_events = list(page_obj.object_list)
        page_fav_map = _favorite_count_map([e.event_id for e in page_events])
        for e in page_events:
            setattr(e, "favorite_count", int(page_fav_map.get(e.event_id, 0)))
    else:
        qs = qs.order_by("title", "event_id")
        paginator = Paginator(qs, size)
        page_obj = paginator.get_page(page)
        page_events = list(page_obj.object_list)
        page_fav_map = _favorite_count_map([e.event_id for e in page_events])
        for e in page_events:
            setattr(e, "favorite_count", int(page_fav_map.get(e.event_id, 0)))

    data = {
        "events": [_event_summary(e) for e in page_events],
        "total_count": paginator.count,
        "total_pages": paginator.num_pages,
        "page": page_obj.number,
        "size": size,
    }
    return common_response(True, data=data, message="성공적으로 목록을 불러옴", status=200)


@require_GET
def event_detail(request, event_id: int):
    try:
        e = Event.objects.get(event_id=event_id)
    except Event.DoesNotExist:
        return common_response(False, message="존재하지 않는 공연 ID", status=404)

    return common_response(True, data=_event_detail(e), message="성공적으로 데이터 반환", status=200)
