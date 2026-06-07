from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from .models import UserProfile
from .utils import (
    create_user_account,
    user_profile_upload_path,
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect(reverse_lazy("dash:dash_home"))

    if request.method == "POST":
        username_or_email = request.POST.get("username")
        password = request.POST.get("password")
        errors = []

        if not username_or_email or not password:
            errors.append(_("Please fill in all required fields."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            # Check if username_or_email is an email
            user_obj = None
            if '@' in username_or_email:
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    username = user_obj.username
                except User.DoesNotExist:
                    username = username_or_email
            else:
                username = username_or_email

            user = authenticate(username=username, password=password)
            if user is not None:
                profile = getattr(user, "profile", None)
                if profile and profile.is_blocked:
                    return JsonResponse(
                        {
                            "success": False,
                            "errors": [
                                _("Your account has been blocked. Please contact support.")
                            ],
                        }
                    )
                login(request, user)
                return JsonResponse(
                    {"success": True, "redirect_url": reverse("dash:dash_home")}
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "errors": [
                            _("Invalid username/email or password. Please try again.")
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

    return render(request, "auth/signup.html")


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


def password_reset_request(request):
    """AJAX view to send password reset email"""
    if request.user.is_authenticated:
        return redirect(reverse_lazy("dash:dash_home"))

    if request.method == "POST":
        email = request.POST.get("email")
        errors = []

        if not email:
            errors.append(_("Email is required."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({
                "success": True,
                "message": _(
                    "If an account with that email exists, a reset link has been sent."
                ),
            })

        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        email_html = render_to_string("auth/password_reset_email.html", {
            "user": user,
            "protocol": "https" if request.is_secure() else "http",
            "domain": request.get_host(),
            "uid": uidb64,
            "token": token,
        })
        email_text = render_to_string("auth/password_reset_email.txt", {
            "user": user,
            "protocol": "https" if request.is_secure() else "http",
            "domain": request.get_host(),
            "uid": uidb64,
            "token": token,
        })

        email_msg = EmailMultiAlternatives(
            subject=_("LOFT Design - Password Reset / Réinitialisation du mot de passe"),
            body=email_text,
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        email_msg.attach_alternative(email_html, "text/html")

        try:
            email_msg.send(fail_silently=False)
        except Exception:
            return JsonResponse({
                "success": False,
                "errors": [_("Failed to send email. Please try again later.")],
            })

        return JsonResponse({
            "success": True,
            "message": _("A password reset link has been sent to your email."),
            "redirect_url": reverse("user_auth:password_reset_done"),
        })

    return render(request, "auth/password_reset.html")


def password_reset_done(request):
    return render(request, "auth/password_reset_done.html")


def password_reset_confirm(request, uidb64, token):
    """AJAX view to set a new password via reset link"""
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
        return render(request, "auth/password_reset_confirm.html", {
            "validlink": False,
        })

    if request.method == "POST":
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")

        errors = []
        if not new_password1:
            errors.append(_("Password is required."))
        elif len(new_password1) < 8:
            errors.append(_("Password must be at least 8 characters long."))
        if new_password1 != new_password2:
            errors.append(_("Passwords do not match."))

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            user.set_password(new_password1)
            user.save()
            return JsonResponse({
                "success": True,
                "message": _("Password reset successfully."),
                "redirect_url": reverse("user_auth:password_reset_complete"),
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": [str(e)]})

    return render(request, "auth/password_reset_confirm.html", {
        "validlink": True,
    })


def password_reset_complete(request):
    return render(request, "auth/password_reset_complete.html")
