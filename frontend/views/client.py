from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal

from user_auth.models import UserProfile
from dashboard.models import Product, PartnerPrice, Order, Notification
from dashboard.utils import notify_user, check_low_stock


@login_required
def client_home(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return redirect("frontend:home")

    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")[:5]
    total_orders = Order.objects.filter(buyer=request.user).count()
    delivered = Order.objects.filter(buyer=request.user, status=Order.OrderStatus.DELIVERED).count()
    pending_count = Order.objects.filter(buyer=request.user, status=Order.OrderStatus.PENDING).count()

    semi_name = ""
    if profile.created_by:
        semi_name = profile.created_by.user.get_full_name() or profile.created_by.user.username

    return render(request, "dash/client_home.html", {
        "orders": orders,
        "total_orders": total_orders,
        "delivered": delivered,
        "pending_count": pending_count,
        "semi_name": semi_name,
        "title": _("My Dashboard"),
    })


@login_required
def client_catalog(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return redirect("frontend:home")
    if not profile.created_by:
        return redirect("frontend:home")

    semi_profile = profile.created_by
    prices = PartnerPrice.objects.filter(
        buyer=semi_profile.user, is_active=True,
    ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")

    catalog = []
    for pp in prices:
        product = pp.product
        if not product.is_active or product.status != Product.ProductStatus.APPROVED:
            continue
        wholesale = pp.wholesale_price or pp.purchase_price
        if wholesale is None:
            continue
        catalog.append({
            "product": product,
            "wholesale_price": float(wholesale),
            "primary_image": product.gallery_images.first(),
            "available_qty": product.quantity,
        })

    return render(request, "dash/client_catalog.html", {
        "catalog": catalog,
        "semi_name": semi_profile.user.get_full_name() or semi_profile.user.username,
        "title": _("Products"),
    })


@login_required
def client_order_create(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return JsonResponse({"success": False, "errors": [_("Permission denied.")]}, status=403)
    if not profile.created_by:
        return JsonResponse({"success": False, "errors": [_("No associated semi-affiliate.")]}, status=400)

    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    product_id = request.POST.get("product_id")
    quantity = request.POST.get("quantity", 1)

    errors = {}
    if not product_id:
        errors["product_id"] = [_("Product is required")]

    try:
        quantity = int(quantity)
        if quantity < 1:
            errors["quantity"] = [_("Quantity must be at least 1")]
    except (ValueError, TypeError):
        errors["quantity"] = [_("Invalid quantity")]

    # Check profile has required fields
    full_name = request.user.get_full_name()
    phone = profile.phone_number
    address = profile.address
    if not full_name:
        errors["profile"] = [_("Please update your profile with your full name first.")]
    if not phone:
        errors["profile"] = [_("Please update your profile with your phone number first.")]

    if errors:
        return JsonResponse({"success": False, "errors": errors})

    semi_profile = profile.created_by
    semi_codes = [semi_profile.affiliate_code] if semi_profile.affiliate_code else []

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().filter(
                pk=product_id, is_active=True, status=Product.ProductStatus.APPROVED
            ).first()
            if not product:
                return JsonResponse({"success": False, "errors": {"product_id": [_("Product not found.")]}})

            pp = PartnerPrice.objects.filter(
                product=product, buyer=semi_profile.user, is_active=True
            ).first()
            if not pp:
                return JsonResponse({"success": False, "errors": {"product_id": [_("Product not available.")]}})

            wholesale = pp.wholesale_price or pp.purchase_price
            if wholesale is None:
                return JsonResponse({"success": False, "errors": {"product_id": [_("Price not configured.")]}})

            if product.quantity < quantity:
                return JsonResponse({
                    "success": False,
                    "errors": {"quantity": [_("Only %(qty)s available.") % {"qty": product.quantity}]}
                })

            order_item = {
                "product_id": product.pk,
                "title": product.title,
                "price": str(wholesale),
                "quantity": quantity,
                "thumbnail": product.thumbnail.url if product.thumbnail else "",
            }

            product.quantity -= quantity
            product.save()
            check_low_stock(product)

            order = Order.objects.create(
                buyer=request.user,
                items=[order_item],
                customer_name=full_name,
                customer_phone=phone,
                customer_address=address or "",
                status=Order.OrderStatus.PENDING,
                referred_by=semi_profile.affiliate_code or "",
            )

            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    admin,
                    _("New Order from End Client"),
                    _("%(name)s ordered %(product)s x%(qty)s through %(semi)s.")
                    % {
                        "name": full_name,
                        "product": product.title,
                        "qty": quantity,
                        "semi": semi_profile.user.get_full_name() or semi_profile.user.username,
                    },
                    notification_type=Notification.NotificationType.SUCCESS,
                    link="/dashboard/orders/",
                )

            if semi_profile.user and not semi_profile.user.is_superuser:
                notify_user(
                    semi_profile.user,
                    _("New Order from Your Client"),
                    _("%(client)s ordered %(product)s x%(qty)s.")
                    % {"client": full_name, "product": product.title, "qty": quantity},
                    notification_type=Notification.NotificationType.INFO,
                    link="/dashboard/orders/",
                )

            return JsonResponse({
                "success": True,
                "message": _("Order placed successfully!"),
                "redirect_url": reverse("frontend:client_orders"),
            })

    except Exception as e:
        return JsonResponse({"success": False, "errors": {"system": [str(e)]}})


@login_required
def client_orders(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return redirect("frontend:home")

    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")

    return render(request, "dash/client_orders.html", {
        "orders": orders,
        "title": _("My Orders"),
    })
