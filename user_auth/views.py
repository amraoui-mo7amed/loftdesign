from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
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


def set_password(request, uidb64, token):
    """
    Allows a user to set their password via a signed link (no prior password needed).
    Used by providers created by admin.
    """
    if request.user.is_authenticated:
        return redirect(reverse_lazy("dash:dash_home"))

    user = None
    valid_link = False

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        token_generator = PasswordResetTokenGenerator()
        if token_generator.check_token(user, token):
            valid_link = True
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass

    if not valid_link:
        return render(request, "auth/set_password.html", {
            "valid_link": False,
        })

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        errors = []
        if not password:
            errors.append(_("Password is required."))
        elif len(password) < 8:
            errors.append(_("Password must be at least 8 characters long."))
        if password != confirm_password:
            errors.append(_("Passwords do not match."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            user.set_password(password)
            user.save()
            # Log the user in immediately
            authenticated_user = authenticate(
                request, username=user.username, password=password
            )
            if authenticated_user:
                login(request, authenticated_user)
                return JsonResponse({
                    "success": True,
                    "message": _("Password set successfully! Welcome to LOFT Design."),
                    "redirect_url": reverse("dash:dash_home"),
                })
            else:
                return JsonResponse({
                    "success": False,
                    "errors": [_("Something went wrong. Please try logging in manually.")],
                })
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})

    return render(request, "auth/set_password.html", {
        "valid_link": True,
        "user": user,
    })
