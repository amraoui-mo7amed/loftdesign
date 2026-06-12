import json

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.db import transaction
from decimal import Decimal
from ..models import Order, Product, PartnerPrice, Notification, LoftPrice
from dashboard.decorator import role_required
from dashboard.utils import notify_user, get_dash_cart, save_dash_cart, DASHBOARD_CART_SESSION_KEY, get_algeria_locations
from user_auth.models import UserProfile

_RC = UserProfile.roleChoices
_AFFILIATE_ROLES = [_RC.AFFILIATE, _RC.SEMI_AFFILIATE]


@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER] + _AFFILIATE_ROLES)
def order_list(request):
    """List orders — admins see all, providers see their products, affiliates see their catalog products"""
    status_filter = request.GET.get("status", "")
    user_profile = getattr(request.user, "profile", None)
    role = user_profile.role if user_profile else None
    is_provider = role == _RC.PROVIDER
    is_affiliate_or_semi = role in _AFFILIATE_ROLES

    if is_provider:
        user_product_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        all_orders = Order.objects.all().order_by("-created_at")
        orders = [o for o in all_orders if any(
            item.get("product_id") in user_product_ids for item in o.items
        )]
    elif is_affiliate_or_semi:
        catalog_ids = set(
            PartnerPrice.objects.filter(
                buyer=request.user, is_active=True
            ).values_list("product_id", flat=True)
        )
        all_orders = Order.objects.all().order_by("-created_at")
        orders = [o for o in all_orders if any(
            item.get("product_id") in catalog_ids for item in o.items
        )]
    else:
        orders = Order.objects.all().order_by("-created_at")
        if status_filter:
            orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for order in page_obj.object_list:
        order.items_json = json.dumps(order.items, ensure_ascii=False)

    # Compute affiliate earnings for DELIVERED orders with referred_by
    delivered_referred = [
        o for o in page_obj.object_list
        if o.referred_by and o.status == Order.OrderStatus.DELIVERED
    ]
    if delivered_referred:
        all_product_ids = set()
        for o in delivered_referred:
            for item in o.items:
                pid = item.get("product_id")
                if pid:
                    all_product_ids.add(pid)
        loft_prices = {
            lp.product_id: lp
            for lp in LoftPrice.objects.filter(product_id__in=all_product_ids)
        }
        for o in delivered_referred:
            earnings = Decimal("0.00")
            for item in o.items:
                product_id = item.get("product_id")
                price = Decimal(str(item.get("price", 0))) or Decimal("0")
                quantity = int(item.get("quantity", 1))
                loft_price = loft_prices.get(product_id)
                if loft_price:
                    margin = price - loft_price.loft_retail_price
                    if margin > 0:
                        earnings += margin * quantity
            o.commission_earned = earnings

    is_trusted = user_profile and user_profile.is_trusted
    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "title": _("Orders"),
        "is_provider": is_provider,
        "is_trusted": is_trusted,
        "is_affiliate_or_semi": is_affiliate_or_semi,
    }
    return render(request, "orders/list.html", context)


@role_required(allowed_roles=_AFFILIATE_ROLES)
def affiliate_cart_checkout(request):
    """Dashboard cart for affiliates — select products + client details → create Order"""
    profile = get_object_or_404(UserProfile, user=request.user)
    cart = get_dash_cart(request)

    catalog_prices = PartnerPrice.objects.filter(
        buyer=request.user, is_active=True
    ).select_related("product", "product__loft_price").prefetch_related("product__gallery_images")

    cart_product_ids = set(cart.keys())

    catalog = []
    for pp in catalog_prices:
        product = pp.product
        loft_price = getattr(product, "loft_price", None)
        pid_str = str(product.pk)
        catalog.append({
            "product": product,
            "partner_price": pp,
            "retail_price": pp.retail_price or (loft_price.loft_retail_price if loft_price else None),
            "primary_image": product.gallery_images.first(),
            "cart_qty": int(cart.get(pid_str, {}).get("quantity", 0)),
        })

    cart_items = []
    for product_id_str, item_data in cart.items():
        try:
            product = Product.objects.get(pk=product_id_str)
        except Product.DoesNotExist:
            continue
        price = Decimal(str(item_data.get("retail_price", 0)))
        qty = int(item_data.get("quantity", 1))
        cart_items.append({
            "product_id": product.pk,
            "title": product.title,
            "price": price,
            "quantity": qty,
            "subtotal": price * qty,
            "thumbnail": product.thumbnail.url if product.thumbnail else "",
        })

    wilaya_options, communes_data = get_algeria_locations()

    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        wilaya = request.POST.get("wilaya")
        commune = request.POST.get("commune")
        address = request.POST.get("address")

        if not name or not phone:
            return JsonResponse({"success": False, "errors": [_("Name and phone are required.")]})

        if not cart_items:
            return JsonResponse({"success": False, "errors": [_("Cart is empty.")]})

        with transaction.atomic():
            order_items = []
            product_titles = []
            for item_data in cart.values():
                product = Product.objects.filter(pk=item_data.get("product_id")).first()
                if not product:
                    continue
                price = Decimal(str(item_data.get("retail_price", 0)))
                qty = int(item_data.get("quantity", 1))
                order_items.append({
                    "product_id": product.pk,
                    "title": product.title,
                    "price": str(price),
                    "quantity": qty,
                    "thumbnail": product.thumbnail.url if product.thumbnail else "",
                })
                product_titles.append(product.title)
                product.quantity -= qty
                product.save()

            Order.objects.create(
                buyer=request.user,
                items=order_items,
                customer_name=name,
                customer_phone=phone,
                customer_address=address,
                wilaya=wilaya,
                commune=commune,
                referred_by=profile.affiliate_code,
            )

        request.session[DASHBOARD_CART_SESSION_KEY] = {}
        request.session.modified = True

        creator_name = request.user.get_full_name() or request.user.username

        # Notify admin
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            notify_user(
                admin,
                _("New Order from %(affiliate)s") % {"affiliate": creator_name},
                _("%(affiliate)s placed an order for %(products)s — Customer: %(name)s")
                % {
                    "affiliate": creator_name,
                    "products": ", ".join(product_titles),
                    "name": name,
                },
                notification_type=Notification.NotificationType.SUCCESS,
                link="/dashboard/orders/",
            )

        # Notify the affiliate/semi-affiliate who created the order
        notify_user(
            request.user,
            _("Order Created Successfully"),
            _("You placed an order for %(products)s — %(name)s. Track it in your orders.")
            % {"products": ", ".join(product_titles), "name": name},
            notification_type=Notification.NotificationType.INFO,
            link="/dashboard/orders/",
        )

        # If semi-affiliate, also notify their parent affiliate
        if profile.role == UserProfile.roleChoices.SEMI_AFFILIATE and profile.parent_affiliate:
            notify_user(
                profile.parent_affiliate.user,
                _("New Order from %(semi)s") % {"semi": creator_name},
                _("%(semi)s placed an order for %(products)s — Customer: %(name)s")
                % {"semi": creator_name, "products": ", ".join(product_titles), "name": name},
                notification_type=Notification.NotificationType.INFO,
                link="/dashboard/orders/",
            )

        return JsonResponse({
            "success": True,
            "message": _("Order created successfully!"),
            "redirect_url": reverse("dash:order_list"),
        })

    cart_product_ids = set(cart.keys())

    cart_total = sum(item["subtotal"] for item in cart_items)

    return render(request, "orders/affiliate_cart.html", {
        "catalog": catalog,
        "cart_items": cart_items,
        "cart_total": cart_total,
        "cart_product_ids": cart_product_ids,
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
        "profile": profile,
        "title": _("Create Order"),
    })


@role_required(allowed_roles=_AFFILIATE_ROLES)
def affiliate_cart_add(request, product_pk):
    """AJAX: Add/update product quantity in dashboard cart"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    product = get_object_or_404(
        Product, pk=product_pk, is_active=True,
        status=Product.ProductStatus.APPROVED
    )
    pp = PartnerPrice.objects.filter(
        product=product, buyer=request.user, is_active=True
    ).first()
    if not pp:
        return JsonResponse({
            "success": False,
            "message": _("Product not in your catalog."),
        })

    retail_price = pp.retail_price
    loft_price = getattr(product, "loft_price", None)
    if not retail_price and loft_price:
        retail_price = loft_price.loft_retail_price

    if not retail_price:
        return JsonResponse({
            "success": False,
            "message": _("No retail price configured for this product."),
        })

    quantity = int(request.POST.get("quantity", 1))
    if quantity < 1:
        quantity = 1
    if quantity > product.quantity:
        return JsonResponse({
            "success": False,
            "message": _("Only %(qty)s available.") % {"qty": product.quantity},
        })

    cart = get_dash_cart(request)
    key = str(product_pk)
    cart[key] = {
        "product_id": product.pk,
        "quantity": quantity,
        "retail_price": str(retail_price),
        "title": product.title,
    }
    save_dash_cart(request, cart)

    return JsonResponse({
        "success": True,
        "message": _("%(title)s added to cart.") % {"title": product.title},
        "cart_count": len(cart),
    })


@role_required(allowed_roles=_AFFILIATE_ROLES)
def affiliate_cart_remove(request, product_pk):
    """AJAX: Remove product from dashboard cart"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    cart = get_dash_cart(request)
    key = str(product_pk)
    removed_title = cart.get(key, {}).get("title", "")
    if key in cart:
        del cart[key]
        save_dash_cart(request, cart)

    return JsonResponse({
        "success": True,
        "message": _("%(title)s removed from cart.") % {"title": removed_title},
        "cart_count": len(cart),
    })


@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER])
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


@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER] + _AFFILIATE_ROLES)
def order_detail(request, pk):
    """View order details with full product list"""
    order = get_object_or_404(Order, pk=pk)
    user_profile = getattr(request.user, "profile", None)
    role = user_profile.role if user_profile else None
    is_provider = role == _RC.PROVIDER
    is_affiliate_or_semi = role in _AFFILIATE_ROLES

    if is_provider:
        own_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        order_ids = {item.get("product_id") for item in order.items}
        if not order_ids.intersection(own_ids):
            return redirect("dash:order_list")
    elif is_affiliate_or_semi:
        catalog_ids = set(
            PartnerPrice.objects.filter(
                buyer=request.user, is_active=True
            ).values_list("product_id", flat=True)
        )
        order_ids = {item.get("product_id") for item in order.items}
        if not order_ids.intersection(catalog_ids):
            return redirect("dash:order_list")

    referred_by_profile = None
    affiliate_earned = None
    if order.referred_by:
        referred_by_profile = UserProfile.objects.filter(
            affiliate_code=order.referred_by
        ).first()
        if referred_by_profile and order.status == Order.OrderStatus.DELIVERED:
            affiliate_earned = Decimal("0.00")
            product_ids = [item.get("product_id") for item in order.items if item.get("product_id")]
            loft_prices = {
                lp.product_id: lp
                for lp in LoftPrice.objects.filter(product_id__in=product_ids)
            }
            for item in order.items:
                product_id = item.get("product_id")
                price = Decimal(str(item.get("price", 0))) or Decimal("0")
                quantity = int(item.get("quantity", 1))
                loft_price = loft_prices.get(product_id)
                if loft_price:
                    margin = price - loft_price.loft_retail_price
                    if margin > 0:
                        affiliate_earned += margin * quantity

    is_trusted = user_profile and user_profile.is_trusted
    return render(request, "orders/detail.html", {
        "order": order,
        "is_provider": is_provider,
        "is_trusted": is_trusted,
        "is_affiliate_or_semi": is_affiliate_or_semi,
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



