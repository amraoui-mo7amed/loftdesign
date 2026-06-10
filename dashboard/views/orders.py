import json

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from decimal import Decimal
from ..models import Order, Product, Notification, LoftPrice
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

    is_trusted = user_profile and user_profile.is_trusted
    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "title": _("Orders"),
        "is_provider": is_provider,
        "is_trusted": is_trusted,
    }
    return render(request, "orders/list.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.PROVIDER])
def order_update_status(request, pk):
    """AJAX view to update order status — only admins and trusted providers"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")

        if new_status not in Order.OrderStatus.values:
            return JsonResponse({"success": False}, status=400)

        user_profile = getattr(request.user, "profile", None)
        is_provider = user_profile and user_profile.role == UserProfile.roleChoices.PROVIDER

        if is_provider:
            if not user_profile.is_trusted:
                return JsonResponse({
                    "success": False,
                    "message": _("Only trusted providers can update order status."),
                })
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

    referred_by_profile = None
    affiliate_earned = None
    if order.referred_by:
        referred_by_profile = UserProfile.objects.filter(
            affiliate_code=order.referred_by
        ).first()
        if referred_by_profile:
            affiliate_earned = Decimal("0.00")
            for item in order.items:
                product_id = item.get("product_id")
                price = Decimal(str(item.get("price", 0))) or Decimal("0")
                quantity = int(item.get("quantity", 1))
                if product_id:
                    try:
                        loft_price = LoftPrice.objects.get(product_id=product_id)
                        margin = price - loft_price.loft_retail_price
                        if margin > 0:
                            affiliate_earned += margin * quantity
                    except LoftPrice.DoesNotExist:
                        pass

    is_trusted = user_profile and user_profile.is_trusted
    return render(request, "orders/detail.html", {
        "order": order,
        "is_provider": is_provider,
        "is_trusted": is_trusted,
        "referred_by_profile": referred_by_profile,
        "affiliate_earned": affiliate_earned,
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


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def order_toggle_commission(request, pk):
    """AJAX: toggle commission_paid on an order"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        order.commission_paid = not order.commission_paid
        order.save(update_fields=["commission_paid"])
        return JsonResponse({
            "success": True,
            "commission_paid": order.commission_paid,
            "message": _("Commission marked as paid") if order.commission_paid else _("Commission marked as unpaid"),
        })
    return JsonResponse({"success": False}, status=400)



