from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.gate, name="gate"),
    path("verify/", views.gate_verify, name="gate_verify"),
    path("exit/", views.sign_out, name="sign_out"),
    path("switch/", views.switch_account, name="switch_account"),
]
