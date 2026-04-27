from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from .models import UserProfile
from .utils import (
    create_user_account,
    user_profile_upload_path,
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(reverse_lazy("dash:dash_home"))

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        errors = []

        if not username or not password:
            errors.append(_("Please fill in all required fields."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse(
                    {"success": True, "redirect_url": reverse("dash:dash_home")}
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": [
                            _("Invalid username or password. Please try again.")
                        ],
                    }
                )
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("user_auth:login")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect(reverse_lazy("dash:dash_home"))

    if request.method == "POST":
        # Extract data
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        phone_number = request.POST.get("phone_number", "")
        sex = request.POST.get("sex")
        birth_date = request.POST.get("birth_date") or None

        errors = []

        # Validation
        if not first_name:
            errors.append(_("First name is required."))
        if not last_name:
            errors.append(_("Last name is required."))
        if not email:
            errors.append(_("Email is required."))
        if not password:
            errors.append(_("Password is required."))
        if password != confirm_password:
            errors.append(_("Passwords do not match."))
        elif len(password) < 8:
            errors.append(_("Password must be at least 8 characters long."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        # Check existing user
        if User.objects.filter(username=email).exists():
            return JsonResponse(
                {"success": False, "errors": [_("This email is already registered.")]}
            )

        try:
            # Data dictionaries for helper
            user_data = {
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
            }
            profile_data = {
                "phone_number": phone_number,
                "sex": sex,
                "birth_date": birth_date,
            }

            user = create_user_account(user_data, profile_data, None)

            return JsonResponse(
                {
                    "success": True,
                    "message": _("Your account has been created successfully."),
                    "redirect_url": reverse("user_auth:login"),
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})

    return render(
        request,
        "auth/signup.html",
        {
            "sex_choices": UserProfile.sexChoices.choices,
        },
    )
