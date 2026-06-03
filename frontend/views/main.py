from django.shortcuts import render
from dashboard.models import Portfolio, Product, SiteSettings, ContactRequest
from django.http import JsonResponse
from django.utils.translation import gettext as _
from dashboard.utils import notify_user
from dashboard.models import Notification
from django.contrib.auth.models import User

def home_view(request):
    latest_portfolios = Portfolio.objects.filter(is_featured=True)[:6]
    if not latest_portfolios.exists():
        latest_portfolios = Portfolio.objects.all()[:6]

    latest_products = Product.objects.filter(is_active=True, is_featured=True)[:4]
    if not latest_products.exists():
        latest_products = Product.objects.filter(is_active=True)[:4]

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
        "latest_portfolios": latest_portfolios,
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
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)

