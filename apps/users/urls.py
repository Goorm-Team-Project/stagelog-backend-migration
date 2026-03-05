from django.urls import path
from .views import (
    get_other_user_info,
    get_user_info,
    update_user_profile,
)

# [auth-service 이전]
# 아래 view들은 auth service로 이관되어 users.urls에서 더 이상 사용하지 않음.
# kakao_login, google_login, naver_login, signup, logout, refresh_token_check, me
# kakao_test_page, kakao_callback_test, google_test_page, google_callback_test

urlpatterns = [
    # [auth-service 이전: route disabled]
    # path('login/kakao', kakao_login, name='kakao_login'),
    # path('login/google', google_login, name='google_login'),
    # path('login/naver', naver_login, name='naver_login'),
    # path('signup', signup, name='signup'),
    # path('logout', logout, name='logout'),
    # path('login/refresh', refresh_token_check, name='refresh_token_check'),
    # path('keep', me, name='me'),
    # path('kakao/test', kakao_test_page),      # 1. 여기로 접속하면 로그인 시작
    # path('callback', kakao_callback_test),
    # path('google/test', google_test_page),       # 시작점
    # path('google/callback', google_callback_test), # 도착점

    # 마이페이지
    path('me', get_user_info, name='get_user_info'),
    #다른 유저 정보 조회
    path('<int:user_id>', get_other_user_info, name='get_other_user_info'),
    #내 정보 수정
    path('me/profile', update_user_profile, name='update_user_profile'),
]
