import json

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from ..models import Order, Product, Notification
from dashboard.decorator import role_required
from dashboard.utils import notify_user
from user_auth.models import UserProfile


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_list(request):
    """View to list all orders — admins see all, providers see only orders containing their products"""
    status_filter = request.GET.get("status", "")
    user_profile = getattr(request.user, "profile", None)
    is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

    if is_provider:
        user_product_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        all_orders = Order.objects.all().order_by("-created_at")
        orders = [o for o in all_orders if any(
            item.get("product_id") in user_product_ids for item in o.items
        )]
        paginator = Paginator(orders, 15)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)
    else:
        orders = Order.objects.all().order_by("-created_at")
        if status_filter:
            orders = orders.filter(status=status_filter)
        paginator = Paginator(orders, 15)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    for order in page_obj.object_list:
        order.items_json = json.dumps(order.items, ensure_ascii=False)

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "title": _("Orders"),
        "is_provider": is_provider,
    }
    return render(request, "orders/list.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_update_status(request, pk):
    """AJAX view to update order status"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")

        if new_status not in Order.OrderStatus.values:
            return JsonResponse({"success": False}, status=400)

        user_profile = getattr(request.user, "profile", None)
        is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

        if is_provider:
            user_product_ids = set(
                Product.objects.filter(user=request.user).values_list("id", flat=True)
            )
            order_product_ids = {item.get("product_id") for item in order.items}
            if not order_product_ids.intersection(user_product_ids):
                return JsonResponse({
                    "success": False,
                    "message": _("You can only update orders for your own products."),
                })

        old_display = order.get_status_display()
        order.status = new_status
        order.save()

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


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_detail(request, pk):
    """View order details with full product list"""
    order = get_object_or_404(Order, pk=pk)
    user_profile = getattr(request.user, "profile", None)
    is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

    if is_provider:
        user_product_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        order_product_ids = {item.get("product_id") for item in order.items}
        if not order_product_ids.intersection(user_product_ids):
            return redirect("dash:order_list")

    return render(request, "orders/detail.html", {
        "order": order,
        "is_provider": is_provider,
        "title": _("Order #%(id)s Details") % {"id": order.id},
    })


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def order_delete(request, pk):
    """AJAX view to delete an order - ADMIN ONLY"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return JsonResponse({"success": True, "message": _("Order removed")})
    return JsonResponse({"success": False}, status=400)



