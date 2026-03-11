'''
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
'''
from django.contrib import admin
from django.urls import path, include

from events import views as events_views
from posts import views as posts_views
from bookmarks import views as bookmarks_views
from uploads import views as uploads_views
from users import views as users_views
from common.utils import health_check

urlpatterns = [
    #admin은 Django 기본 구조상 prefix에 / 포함
    path('admin/', admin.site.urls),

    # Auth / Users (login 라우팅)
    # NOTE: auth service 분리로 인해 다음 라우트는 임시 제거 대상
    # path('api/auth/', include('users.urls')),
    path('api/users/', include('users.urls')),

    # Internal APIs (service-to-service)
    path("internal/users:batch-get", users_views.internal_users_batch_get, name="internal_users_batch_get"),
    path("internal/users/<int:user_id>/exp", users_views.internal_apply_user_exp, name="internal_apply_user_exp"),
    path("internal/events/<int:event_id>/exists", events_views.internal_event_exists, name="internal_event_exists"),
    path("internal/events/<int:event_id>/summary", events_views.internal_event_summary, name="internal_event_summary"),
    path("internal/events:batch-summary", events_views.internal_events_batch_summary, name="internal_events_batch_summary"),
    path(
        "internal/bookmarks/events:favorite-count",
        bookmarks_views.internal_bookmark_favorite_count,
        name="internal_bookmark_favorite_count",
    ),

    # Bookmarks 라우팅
    path('api/bookmarks/', include('bookmarks.urls')),

    # Events (events 라우팅)
    ## /api/events
    path('api/events', events_views.event_list, name='event_list'),
    ## /api/events/<id> ...
    path('api/events/', include('events.urls')),

    # Posts (posts 라우팅)
    path('api/posts', posts_views.posts_list, name='posts_list'),
    path('api/posts/', include('posts.urls')),

    # Comments 라우팅
    path('api/comments/', include('posts.comment_urls')),

    # Notifications 라우팅 [notification-service 이관]
    # path('api/notifications', notifications_views.get_notification_list, name='get_notification_list'),
    # path('api/notifications/', include('notifications.urls')),

    path('', health_check),

    path("api/uploads/presign", uploads_views.presign_upload, name="presign_upload"),
]
