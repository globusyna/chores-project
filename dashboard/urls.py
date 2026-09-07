from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("board/", views.board, name="board"),
    path("board/<int:pk>/claim/", views.claim_bounty, name="claim_bounty"),
    path("board/<int:pk>/submit/", views.submit_bounty, name="submit_bounty"),
    path("review/", views.review_queue, name="review_queue"),
    path("review/<int:pk>/approve/", views.approve_bounty, name="approve_bounty"),
    path("review/<int:pk>/reject/", views.reject_bounty, name="reject_bounty"),
]
