from django.urls import path
from . import views

urlpatterns = [
    # 목록은 config에서 /api/events로 직접 매핑 path('', views.event_list, name='event_list'),
    path('<int:event_id>', views.event_detail, name='event_detail'),
]
