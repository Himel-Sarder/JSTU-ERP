from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("notice/<int:pk>/", views.notice_detail, name="notice_detail"),
]
