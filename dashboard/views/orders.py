from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from ..models import Order, Notification
from dashboard.decorator import role_required
from dashboard.utils import notify_user
from user_auth.models import UserProfile

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_list(request):
    """View to list orders — admins see all, providers see only their own"""
    status_filter = request.GET.get("status", "")
    user_profile = getattr(request.user, "profile", None)
    is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

    if is_provider:
        orders = Order.objects.filter(product__user=request.user).select_related("product")
    else:
        orders = Order.objects.all().select_related("product")

    if status_filter:
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "title": _("Order Management"),
        "is_provider": is_provider,
    }
    return render(request, "orders/list.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_update_status(request, pk):
    """AJAX view to update order status — providers can only update their own product orders"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")

        if new_status not in Order.OrderStatus.values:
            return JsonResponse({"success": False}, status=400)

        user_profile = getattr(request.user, "profile", None)
        is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

        # Providers can only update orders for their own products
        if is_provider and (not order.product or order.product.user != request.user):
            return JsonResponse({
                "success": False,
                "message": _("You can only update orders for your own products."),
            })

        old_display = order.get_status_display()
        order.status = new_status
        order.save()

        # Notify all admins when a provider changes an order status
        if is_provider:
            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    user=admin,
                    title=_("Order #%(id)s Status Updated") % {"id": order.id},
                    message=_(
                        "%(provider)s changed order #%(id)s from «%(old)s» to «%(new)s»"
                    ) % {
                        "provider": request.user.get_full_name() or request.user.username,
                        "id": order.id,
                        "old": old_display,
                        "new": dict(Order.OrderStatus.choices).get(new_status, new_status),
                    },
                    notification_type=Notification.NotificationType.INFO,
                    link="/dashboard/orders/",
                )

        return JsonResponse({"success": True, "message": _("Order status updated")})

    return JsonResponse({"success": False}, status=400)

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def order_delete(request, pk):
    """AJAX view to delete an order - ADMIN ONLY"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return JsonResponse({"success": True, "message": _("Order removed")})
    return JsonResponse({"success": False}, status=400)
