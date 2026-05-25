from django.urls import path
from . import views

app_name = "user_auth"

urlpatterns = [
    path("login/", views.login_view, name="login"),
   # path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("set-password/<uidb64>/<token>/", views.set_password, name="set_password"),
]
