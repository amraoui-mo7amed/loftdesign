from django.urls import path
from . import views

app_name = "user_auth"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("set-password/<uidb64>/<token>/", views.set_password, name="set_password"),
    # Password Reset
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/done/", views.password_reset_done, name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("password-reset-complete/", views.password_reset_complete, name="password_reset_complete"),
]
