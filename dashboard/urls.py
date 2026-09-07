from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("board/", views.board, name="board"),
    path("board/<int:pk>/claim/", views.claim_bounty, name="claim_bounty"),
]
