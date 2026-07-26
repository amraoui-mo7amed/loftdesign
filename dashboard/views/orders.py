import json

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from ..models import Order, Product, PartnerPrice, Notification
from dashboard.decorator import role_required
from dashboard.utils import notify_user, get_dash_cart, save_dash_cart, DASHBOARD_CART_SESSION_KEY, get_algeria_locations, check_low_stock, compute_item_profit
from user_auth.models import UserProfile

_RC = UserProfile.roleChoices
_AFFILIATE_ROLES = [_RC.AFFILIATE, _RC.SEMI_AFFILIATE]
_VIEWER_ROLES = [*_AFFILIATE_ROLES, _RC.FINAL_CLIENT]


def _admin_transitions_for_order(order):
    """Admin transitions — hides SUPPLIER_FULFILLING if no provider involved."""
    has_provider = False
    for item in order.items:
        pid = item.get("product_id")
        if pid:
            try:
                p = Product.objects.get(pk=pid)
                if p.user and not p.user.is_superuser:
                    has_provider = True
                    break
            except Product.DoesNotExist:
                pass

    transitions = {
        Order.OrderStatus.PENDING: [
            Order.OrderStatus.ADMIN_VALIDATED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.STORE_VALIDATED: [
            Order.OrderStatus.ADMIN_VALIDATED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.SHIPPED: [
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ],
    }

    if has_provider:
        transitions[Order.OrderStatus.ADMIN_VALIDATED] = [
            Order.OrderStatus.CANCELLED,
        ]
        transitions[Order.OrderStatus.SUPPLIER_FULFILLING] = [
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ]
    else:
        # Admin-created product — no validation needed, ship/deliver directly
        transitions[Order.OrderStatus.PENDING] = [
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ]
        transitions[Order.OrderStatus.ADMIN_VALIDATED] = []
        transitions[Order.OrderStatus.SUPPLIER_FULFILLING] = []

    return transitions


ORDER_TRANSITIONS = {
    _RC.ADMIN.value: {
        Order.OrderStatus.PENDING: [
            Order.OrderStatus.ADMIN_VALIDATED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.STORE_VALIDATED: [
            Order.OrderStatus.ADMIN_VALIDATED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.ADMIN_VALIDATED: [
            Order.OrderStatus.SUPPLIER_FULFILLING,
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.SUPPLIER_FULFILLING: [
            Order.OrderStatus.SHIPPED,
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ],
        Order.OrderStatus.SHIPPED: [
            Order.OrderStatus.DELIVERED,
            Order.OrderStatus.CANCELLED,
        ],
    },
    _RC.PROVIDER.value: {
        Order.OrderStatus.ADMIN_VALIDATED: [
            Order.OrderStatus.SUPPLIER_FULFILLING,
        ],
    },
    _RC.SEMI_AFFILIATE.value: {},
}


@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER] + _VIEWER_ROLES)
def order_list(request):
    """List orders — admins see all, providers see their products, affiliates see their catalog products"""
    user_profile = getattr(request.user, "profile", None)
    role = user_profile.role if user_profile else None

    if role == _RC.PROVIDER and (not user_profile or not user_profile.is_trusted):
        raise PermissionDenied(_("Only trusted providers can access this page."))

    status_filter = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    is_admin = role == _RC.ADMIN or request.user.is_superuser
    is_provider = (not request.user.is_superuser) and role == _RC.PROVIDER
    is_affiliate_or_semi = role in _AFFILIATE_ROLES
    is_end_client = role == _RC.FINAL_CLIENT

    if is_end_client:
        orders = Order.objects.filter(buyer=request.user).order_by("-created_at")
        if status_filter:
            orders = orders.filter(status=status_filter)
    elif is_provider:
        user_product_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        all_orders = Order.objects.all().order_by("-created_at")
        orders = [o for o in all_orders if any(
            item.get("product_id") in user_product_ids for item in o.items
        )]
    elif is_affiliate_or_semi:
        profile = getattr(request.user, "profile", None)
        referred_codes = []
        if profile and profile.affiliate_code:
            referred_codes.append(profile.affiliate_code)
            if profile.role == _RC.AFFILIATE:
                semi_codes = UserProfile.objects.filter(
                    parent_affiliate=profile, is_approved=True
                ).exclude(affiliate_code__isnull=True).exclude(affiliate_code="").values_list("affiliate_code", flat=True)
                referred_codes.extend(semi_codes)
        orders = Order.objects.filter(referred_by__in=referred_codes).order_by("-created_at")
        if status_filter:
            orders = orders.filter(status=status_filter)
    else:
        orders = Order.objects.all().order_by("-created_at")
        if status_filter:
            orders = orders.filter(status=status_filter)

    if q:
        if isinstance(orders, list):
            orders = [o for o in orders if q.lower() in (o.customer_name or "").lower() or q.lower() in (o.customer_phone or "").lower()]
        else:
            orders = orders.filter(
                Q(customer_name__icontains=q) | Q(customer_phone__icontains=q)
            )

    paginator = Paginator(orders, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for order in page_obj.object_list:
        order.items_json = json.dumps(order.items, ensure_ascii=False)
        # Per-order allowed transitions for the current user
        if is_admin:
            transitions = _admin_transitions_for_order(order)
        elif is_end_client:
            transitions = {}
        else:
            transitions = ORDER_TRANSITIONS.get(role, {})
        allowed_statuses = transitions.get(order.status, [])
        order.allowed_next_statuses = [
            {"value": s, "label": _(dict(Order.OrderStatus.choices)[s])}
            for s in allowed_statuses
        ]
        # Chain breakdown for admin
        order.chain_details_json = None
        order.profit_breakdown = []
        if order.referred_by and order.status == Order.OrderStatus.DELIVERED and is_admin:
            from dashboard.utils import build_order_chain_breakdown
            chain_data = build_order_chain_breakdown(order)
            order.chain_details_json = json.dumps(chain_data)
            # Per-item profit breakdown
            for item in order.items:
                pid = item.get("product_id")
                price = item.get("price", 0)
                qty = item.get("quantity", 1)
                title = item.get("title", "")
                if pid:
                    try:
                        p = Product.objects.get(pk=pid)
                        profit = compute_item_profit(p, price, qty, order.referred_by)
                        order.profit_breakdown.append({
                            "title": title,
                            "qty": qty,
                            "price": float(price) * int(qty),
                            "supplier": float(profit["supplier_share"]),
                            "loft": float(profit["loft_share"]),
                            "affiliate": float(profit["affiliate_share"]),
                            "semi": float(profit["semi_share"]),
                        })
                    except Product.DoesNotExist:
                        pass
        order.profit_breakdown_json = json.dumps(order.profit_breakdown)

    is_trusted = user_profile and user_profile.is_trusted

    status_options = [
        {"value": s, "label": _(l)} for s, l in Order.OrderStatus.choices
    ]
    selected_status_label = None
    for so in status_options:
        if so["value"] == status_filter:
            selected_status_label = so["label"]
            break

    filter_params = {}
    if q:
        filter_params["q"] = q
    if status_filter:
        filter_params["status"] = status_filter
    base_query = "&".join(f"{k}={v}" for k, v in filter_params.items())
    base_url = f"?{base_query}&" if base_query else "?"

    context = {
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": Order.OrderStatus.choices,
        "status_options": status_options,
        "selected_status_label": selected_status_label,
        "q": q,
        "filter_params": filter_params,
        "base_url": base_url,
        "title": _("Orders"),
        "is_admin": is_admin,
        "is_provider": is_provider,
        "is_trusted": is_trusted,
        "is_affiliate_or_semi": is_affiliate_or_semi,
        "is_end_client": is_end_client,
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
                check_low_stock(product)

            order = Order.objects.create(
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
        request.session.pop("affiliate_code", None)
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


@role_required(allowed_roles=[_RC.ADMIN, _RC.PROVIDER] + _AFFILIATE_ROLES)
def order_update_status(request, pk):
    """AJAX view to update order status with role-based transitions"""
    if request.method == "POST":
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")

        if new_status not in Order.OrderStatus.values:
            return JsonResponse({"success": False}, status=400)

        user_profile = getattr(request.user, "profile", None)
        role = user_profile.role if user_profile else None
        is_superuser = request.user.is_superuser
        is_admin = role == _RC.ADMIN or is_superuser
        is_provider = (not is_superuser) and role == _RC.PROVIDER
        is_affiliate = (not is_superuser) and role == _RC.AFFILIATE
        is_semi = (not is_superuser) and role == _RC.SEMI_AFFILIATE

        # Permission matrix — use transitions for the role
        role_value = user_profile.role if user_profile else None
        role_transitions = _admin_transitions_for_order(order) if is_admin else ORDER_TRANSITIONS.get(role_value, {})

        if is_admin:
            allowed = role_transitions.get(order.status, [])
            if new_status not in allowed:
                return JsonResponse({
                    "success": False,
                    "message": _("Admin cannot change from %(current)s to %(new)s.") % {
                        "current": order.get_status_display(),
                        "new": dict(Order.OrderStatus.choices).get(new_status, new_status),
                    },
                })
        elif is_provider:
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
            allowed = role_transitions.get(order.status, [])
            if new_status not in allowed:
                return JsonResponse({
                    "success": False,
                    "message": _("You cannot change from %(current)s to %(new)s.") % {
                        "current": order.get_status_display(),
                        "new": dict(Order.OrderStatus.choices).get(new_status, new_status),
                    },
                })
        elif is_affiliate or is_semi:
            allowed = role_transitions.get(order.status, [])
            if new_status not in allowed:
                return JsonResponse({
                    "success": False,
                    "message": _("You can only validate pending orders."),
                })
            # Ensure they can only validate their own orders
            profile = getattr(request.user, "profile", None)
            if not profile or not profile.affiliate_code:
                return JsonResponse({"success": False, "message": _("Permission denied.")})
            if is_affiliate:
                valid_codes = [profile.affiliate_code]
                semi_codes = UserProfile.objects.filter(
                    parent_affiliate=profile, is_approved=True
                ).exclude(affiliate_code__isnull=True).values_list("affiliate_code", flat=True)
                valid_codes.extend(semi_codes)
            else:
                valid_codes = [profile.affiliate_code]
            if order.referred_by not in valid_codes:
                return JsonResponse({"success": False, "message": _("Permission denied.")})

        old_display = order.get_status_display()
        order.status = new_status

        with transaction.atomic():
            # If order is marked DELIVERED, compute profit and credit wallets
            if new_status == Order.OrderStatus.DELIVERED:
                from dashboard.utils import compute_order_profit, credit_wallets_for_order
                compute_order_profit(order)
                credit_wallets_for_order(order)

            order.save()

            # ── Find all relevant parties for notifications ─────────
            admins = User.objects.filter(is_superuser=True)

            provider_ids = set()
            for item in order.items:
                pid = item.get("product_id")
                if pid:
                    try:
                        p = Product.objects.get(pk=pid)
                        if p.user:
                            provider_ids.add(p.user)
                    except Product.DoesNotExist:
                        pass

            referred_user = None
            if order.referred_by:
                ref_profile = UserProfile.objects.filter(
                    affiliate_code=order.referred_by, is_approved=True
                ).first()
                if ref_profile:
                    referred_user = ref_profile.user

            order_label = order.order_number or f"#{order.id}"
            actor_name = request.user.get_full_name() or request.user.username

            # ── Status-specific notifications ───────────────────────
            if new_status == Order.OrderStatus.STORE_VALIDATED:
                for admin in admins:
                    notify_user(
                        admin,
                        _("Order #%(num)s Validated") % {"num": order_label},
                        _('%(name)s validated order #%(num)s.') % {"name": actor_name, "num": order_label},
                        notification_type="info",
                        link="/dashboard/orders/",
                    )

            elif new_status == Order.OrderStatus.ADMIN_VALIDATED:
                for provider in provider_ids:
                    if provider and provider != request.user:
                        notify_user(
                            provider,
                            _("Order Ready for Fulfillment"),
                            _('Order #%(num)s has been validated and is ready for your fulfillment.')
                            % {"num": order_label},
                            notification_type="info",
                            link="/dashboard/orders/",
                        )
                if referred_user and referred_user != request.user and not referred_user.is_superuser:
                    notify_user(
                        referred_user,
                        _("Order #%(num)s Validated") % {"num": order_label},
                        _('Loft Design validated order #%(num)s.') % {"num": order_label},
                        notification_type="info",
                        link="/dashboard/orders/",
                    )

            elif new_status == Order.OrderStatus.SUPPLIER_FULFILLING:
                if not is_admin:
                    for admin in admins:
                        notify_user(
                            admin,
                            _("Order Ready for Delivery"),
                            _('Provider marked order #%(num)s as fulfilled — ready for delivery.')
                            % {"num": order_label},
                            notification_type="info",
                            link="/dashboard/orders/",
                        )
                if referred_user and referred_user != request.user and not referred_user.is_superuser:
                    notify_user(
                        referred_user,
                        _("Order #%(num)s Being Fulfilled") % {"num": order_label},
                        _('Order #%(num)s is now being fulfilled by the supplier.')
                        % {"num": order_label},
                        notification_type="info",
                        link="/dashboard/orders/",
                    )

            elif new_status == Order.OrderStatus.SHIPPED:
                for provider in provider_ids:
                    if provider and provider != request.user:
                        notify_user(
                            provider,
                            _("Order #%(num)s Shipped") % {"num": order_label},
                            _('Order #%(num)s has been shipped.') % {"num": order_label},
                            notification_type="info",
                            link="/dashboard/orders/",
                        )
                if referred_user and referred_user != request.user and not referred_user.is_superuser:
                    notify_user(
                        referred_user,
                        _("Order #%(num)s Shipped") % {"num": order_label},
                        _('Order #%(num)s has been shipped.') % {"num": order_label},
                        notification_type="info",
                        link="/dashboard/orders/",
                    )

            elif new_status == Order.OrderStatus.DELIVERED:
                for provider in provider_ids:
                    if provider and provider != request.user:
                        notify_user(
                            provider,
                            _("Order #%(num)s Delivered") % {"num": order_label},
                            _('Order #%(num)s has been delivered.') % {"num": order_label},
                            notification_type="success",
                            link="/dashboard/orders/",
                        )
                if referred_user and referred_user != request.user and not referred_user.is_superuser:
                    notify_user(
                        referred_user,
                        _("Order #%(num)s Delivered — Commission Earned") % {"num": order_label},
                        _('Order #%(num)s has been delivered. Your commission has been credited to your wallet.')
                        % {"num": order_label},
                        notification_type="success",
                        link="/dashboard/wallet/",
                    )

            elif new_status == Order.OrderStatus.CANCELLED:
                for provider in provider_ids:
                    if provider and provider != request.user:
                        notify_user(
                            provider,
                            _("Order #%(num)s Cancelled") % {"num": order_label},
                            _('Order #%(num)s has been cancelled by %(name)s.')
                            % {"num": order_label, "name": actor_name},
                            notification_type="warning",
                            link="/dashboard/orders/",
                        )
                if referred_user and referred_user != request.user and not referred_user.is_superuser:
                    notify_user(
                        referred_user,
                        _("Order #%(num)s Cancelled") % {"num": order_label},
                        _('Order #%(num)s has been cancelled by %(name)s.')
                        % {"num": order_label, "name": actor_name},
                        notification_type="warning",
                        link="/dashboard/orders/",
                    )
                for admin in admins:
                    if admin != request.user:
                        notify_user(
                            admin,
                            _("Order #%(num)s Cancelled") % {"num": order_label},
                            _('Order #%(num)s has been cancelled by %(name)s.')
                            % {"num": order_label, "name": actor_name},
                            notification_type="warning",
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
    is_superuser = request.user.is_superuser
    is_provider = (not is_superuser) and role == _RC.PROVIDER
    is_affiliate_or_semi = (not is_superuser) and role in _AFFILIATE_ROLES

    if is_provider:
        own_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        order_ids = {item.get("product_id") for item in order.items}
        if not order_ids.intersection(own_ids):
            return redirect("dash:order_list")
    elif is_affiliate_or_semi:
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.affiliate_code:
            return redirect("dash:order_list")
        if order.referred_by != profile.affiliate_code:
            if profile.role != _RC.AFFILIATE:
                return redirect("dash:order_list")
            semi_codes = set(
                UserProfile.objects.filter(
                    parent_affiliate=profile, is_approved=True
                ).exclude(affiliate_code__isnull=True).exclude(affiliate_code="").values_list("affiliate_code", flat=True)
            )
            if order.referred_by not in semi_codes:
                return redirect("dash:order_list")

    referred_by_profile = None
    parent_profile = None
    affiliate_earned = None
    if order.referred_by:
        referred_by_profile = UserProfile.objects.select_related("parent_affiliate").filter(
            affiliate_code=order.referred_by
        ).first()
        if referred_by_profile and referred_by_profile.parent_affiliate:
            parent_profile = referred_by_profile.parent_affiliate
        elif referred_by_profile and referred_by_profile.role == _RC.SEMI_AFFILIATE:
            parent_profile = UserProfile.objects.filter(
                semi_affiliates=referred_by_profile
            ).first()
    if order.referred_by and order.status == Order.OrderStatus.DELIVERED:
        affiliate_earned = (order.affiliate_share or 0) + (order.semi_share or 0)

    is_trusted = user_profile and user_profile.is_trusted
    is_admin = role == _RC.ADMIN or request.user.is_superuser
    return render(request, "orders/detail.html", {
        "order": order,
        "is_provider": is_provider,
        "is_trusted": is_trusted,
        "is_affiliate_or_semi": is_affiliate_or_semi,
        "is_admin": is_admin,
        "referred_by_profile": referred_by_profile,
        "parent_profile": parent_profile,
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



