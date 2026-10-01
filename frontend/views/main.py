from django.shortcuts import render
from dashboard.models import Product, SiteSettings, ContactRequest
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext as _
from dashboard.utils import notify_user
from dashboard.models import Notification
from django.contrib.auth.models import User
from user_auth.utils import create_affiliate_account
import logging

logger = logging.getLogger(__name__)

def home_view(request):
    if request.session.get("affiliate_code"):
        del request.session["affiliate_code"]
        request.session.modified = True

    latest_products = Product.objects.filter(is_active=True, is_featured=True, show_in_global_store=True)[:4]
    if not latest_products.exists():
        latest_products = Product.objects.filter(is_active=True, show_in_global_store=True)[:4]

    settings_obj = SiteSettings.objects.first()
    
    # Extract slider images if settings exist
    slider_images = []
    if settings_obj:
        for img_row in settings_obj.slider_images.all():
            if img_row.image:
                slider_images.append(img_row.image.url)

    # Fallback to static if no database settings slider images exist
    if not slider_images:
        slider_images = [
            "/static/img/header_bg_1.jpeg",
            "/static/img/header_bg_2.jpeg",
            "/static/img/header_bg_3.jpeg",
            "/static/img/header_bg_4.jpeg",
            "/static/img/header_bg_5.jpeg",
        ]

    context = {
        "latest_products": latest_products,
        "slider_images": slider_images,
    }
    return render(request, "home.html", context)

def contact_request_submit(request):
    """AJAX view to handle contact form submission"""
    if request.method == "POST":
        full_name = request.POST.get("name")
        phone_number = request.POST.get("phone")
        project_type = request.POST.get("project_type")
        message = request.POST.get("message")

        errors = {}
        if not full_name: errors["name"] = [_("Full Name is required")]
        if not phone_number: errors["phone"] = [_("Phone Number is required")]
        if not message: errors["message"] = [_("Message is required")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            ContactRequest.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                project_type=project_type,
                message=message
            )

            # Notify Admins via SSE Notification
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    user=admin,
                    title=_("New Contact Request"),
                    message=_("New contact lead from %(name)s") % {"name": full_name},
                    notification_type=Notification.NotificationType.INFO,
                    link="/dashboard/leads/"
                )

            return JsonResponse({
                "success": True,
                "message": _("Your contact request has been sent successfully. We will get back to you shortly.")
            })
        except Exception as e:
            logger.exception("frontend/views/main.py: request failed")
            return JsonResponse({"success": False, "errors": {"system": [_("Something went wrong. Please try again.")]}})

    return JsonResponse({"success": False}, status=400)


def affiliate_signup(request):
    """AJAX view for affiliate registration — account created inactive until admin approves."""
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        errors = {}
        if not first_name:
            errors["first_name"] = [_("First name is required.")]
        if not last_name:
            errors["last_name"] = [_("Last name is required.")]
        if not email:
            errors["email"] = [_("Email is required.")]
        if not password:
            errors["password"] = [_("Password is required.")]
        elif len(password) < 8:
            errors["password"] = [_("Password must be at least 8 characters.")]
        if password != confirm_password:
            errors["confirm_password"] = [_("Passwords do not match.")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        if User.objects.filter(email=email).exists():
            return JsonResponse({
                "success": False,
                "errors": {"email": [_("This email is already registered.")]},
            })

        try:
            user_data = {
                "email": email,
                "password": password,
                "first_name": first_name,
                "last_name": last_name,
            }
            profile_data = {
                "phone_number": phone or "",
            }

            user, affiliate_code = create_affiliate_account(user_data, profile_data)

            # Notify all admins
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    user=admin,
                    title=_("New Affiliate Signup"),
                    message=_(
                        "%(name)s (%(email)s) has registered as an affiliate and is awaiting approval."
                    ) % {"name": f"{first_name} {last_name}", "email": email},
                    notification_type=Notification.NotificationType.INFO,
                    link=reverse("dash:user_details", kwargs={"pk": user.profile.pk}),
                )

            return JsonResponse({
                "success": True,
                "message": _(
                    "Your affiliate account has been created! An admin will review and activate your account. "
                    "You will receive an email once approved."
                ),
            })
        except Exception as e:
            logger.exception("frontend/views/main.py: request failed")
            return JsonResponse({
                "success": False,
                "errors": {"system": [_("Something went wrong. Please try again.")]},
            })

    return JsonResponse({"success": False}, status=400)

