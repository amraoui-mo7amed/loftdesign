from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from dashboard.models import Product, Order, Notification
from dashboard.utils import notify_user
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.db import transaction

def place_order(request):
    """AJAX view to handle product inquiry (order) submission"""
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        wilaya = request.POST.get("wilaya")
        commune = request.POST.get("commune")

        errors = {}
        if not name: errors["name"] = [_("Name is required")]
        if not phone: errors["phone"] = [_("Phone is required")]
        if not wilaya: errors["wilaya"] = [_("Wilaya is required")]
        if not commune: errors["commune"] = [_("Commune is required")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        product = get_object_or_404(Product, id=product_id)

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    product=product,
                    customer_name=name,
                    customer_phone=phone,
                    customer_address=address,
                    wilaya=wilaya,
                    commune=commune,
                    status=Order.OrderStatus.PENDING
                )

                # Notify Admins
                admins = User.objects.filter(is_superuser=True)
                for admin in admins:
                    notify_user(
                        user=admin,
                        title=_("New Lead Received"),
                        message=_("New inquiry from %(name)s for product: %(product)s") % {
                            "name": name,
                            "product": product.title
                        },
                        notification_type=Notification.NotificationType.SUCCESS,
                        link=f"/dashboard/orders/" # Could be more specific if detail view exists
                    )

                return JsonResponse({
                    "success": True,
                    "message": _("Your inquiry has been sent successfully. Our team will contact you soon.")
                })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)
