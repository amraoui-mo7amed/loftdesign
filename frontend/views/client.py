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
from dashboard.utils import notify_user, check_low_stock, snapshot_order, PricingError
import logging

logger = logging.getLogger(__name__)


_CLIENT_ROLES = (UserProfile.roleChoices.FINAL_CLIENT, UserProfile.roleChoices.PROFESSIONAL_CLIENT)


@login_required
def client_home(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role not in _CLIENT_ROLES:
        return redirect("frontend:home")

    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")[:5]
    total_orders = Order.objects.filter(buyer=request.user).count()
    delivered = Order.objects.filter(buyer=request.user, status=Order.OrderStatus.DELIVERED).count()
    pending_count = Order.objects.filter(buyer=request.user, status=Order.OrderStatus.PENDING).count()

    creator_name = ""
    if profile.created_by:
        creator_name = profile.created_by.user.get_full_name() or profile.created_by.user.username

    return render(request, "dash/client_home.html", {
        "orders": orders,
        "total_orders": total_orders,
        "delivered": delivered,
        "pending_count": pending_count,
        "semi_name": creator_name,
        "title": _("My Dashboard"),
    })


@login_required
def client_catalog(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return redirect("frontend:home")
    if not profile.created_by:
        return redirect("frontend:home")

    creator = profile.created_by
    if creator is None:
        return JsonResponse({"success": False, "errors": {"system": [_("Your account is not linked to a store. Please contact us.")]}})
    creator_name = creator.user.get_full_name() or creator.user.username
    catalog = []

    if creator.role == UserProfile.roleChoices.ADMIN:
        products = Product.objects.filter(
            show_in_admin_store=True, is_active=True,
            status=Product.ProductStatus.APPROVED,
        ).select_related("loft_price").prefetch_related("gallery_images")
        for product in products:
            loft_price = getattr(product, "loft_price", None)
            price = loft_price.loft_retail_price if loft_price else None
            if price is None:
                continue
            catalog.append({
                "product": product,
                "wholesale_price": float(price),
                "primary_image": product.gallery_images.first(),
                "available_qty": product.quantity,
            })
    elif creator.role == UserProfile.roleChoices.AFFILIATE:
        prices = PartnerPrice.objects.filter(
            buyer=creator.user, is_active=True,
        ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")
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
    else:
        prices = PartnerPrice.objects.filter(
            buyer=creator.user, is_active=True,
        ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")
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
        "semi_name": creator_name,
        "title": _("Products"),
    })


@login_required
def client_order_create(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != UserProfile.roleChoices.FINAL_CLIENT:
        return JsonResponse({"success": False, "errors": [_("Permission denied.")]}, status=403)
    if not profile.created_by:
        return JsonResponse({"success": False, "errors": [_("No associated partner.")]}, status=400)

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

    if errors:
        return JsonResponse({"success": False, "errors": errors})

    creator = profile.created_by
    if creator is None:
        return JsonResponse({"success": False, "errors": {"system": [_("Your account is not linked to a store. Please contact us.")]}})
    creator_name = creator.user.get_full_name() or creator.user.username

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().filter(
                pk=product_id, is_active=True, status=Product.ProductStatus.APPROVED
            ).first()
            if not product:
                return JsonResponse({"success": False, "errors": {"product_id": [_("Product not found.")]}})

            if product.quantity < quantity:
                return JsonResponse({
                    "success": False,
                    "errors": {"quantity": [_("Only %(qty)s available.") % {"qty": product.quantity}]}
                })

            # Resolve price and referred_by based on creator role
            if creator.role == UserProfile.roleChoices.ADMIN:
                if not product.show_in_admin_store:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Product not available.")]}})
                loft_price = getattr(product, "loft_price", None)
                if not loft_price or not loft_price.loft_retail_price:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Price not configured.")]}})
                unit_price = loft_price.loft_retail_price
                referred_by = ""
            elif creator.role == UserProfile.roleChoices.AFFILIATE:
                pp = PartnerPrice.objects.filter(
                    product=product, buyer=creator.user, is_active=True
                ).first()
                if not pp:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Product not available.")]}})
                unit_price = pp.wholesale_price or pp.purchase_price
                if unit_price is None:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Price not configured.")]}})
                referred_by = creator.affiliate_code or ""
            else:
                pp = PartnerPrice.objects.filter(
                    product=product, buyer=creator.user, is_active=True
                ).first()
                if not pp:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Product not available.")]}})
                unit_price = pp.wholesale_price or pp.purchase_price
                if unit_price is None:
                    return JsonResponse({"success": False, "errors": {"product_id": [_("Price not configured.")]}})
                referred_by = creator.affiliate_code or ""

            order_item = {
                "product_id": product.pk,
                "title": product.title,
                "price": str(unit_price),
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
                referred_by=referred_by,
            )

            # The order follows the normal flow (validation, shipping, delivery);
            # commissions are paid only once it is really delivered.
            snapshot_order(order)

            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    admin,
                    _("New Order from End Client"),
                    _("%(name)s ordered %(product)s x%(qty)s through %(creator)s.")
                    % {
                        "name": full_name,
                        "product": product.title,
                        "qty": quantity,
                        "creator": creator_name,
                    },
                    notification_type=Notification.NotificationType.SUCCESS,
                    link="/dashboard/orders/",
                )

            if creator.user and not creator.user.is_superuser:
                notify_user(
                    creator.user,
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

    except PricingError:
        return JsonResponse({"success": False, "errors": {"system": [_("This product's price is not configured correctly. Please contact the store.")]}})
    except Exception:
        logger.exception("client order failed")
        return JsonResponse({"success": False, "errors": {"system": [_("The order could not be placed. Please try again.")]}})


@login_required
def client_orders(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role not in _CLIENT_ROLES:
        return redirect("frontend:home")

    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")

    return render(request, "dash/client_orders.html", {
        "orders": orders,
        "title": _("My Orders"),
    })
