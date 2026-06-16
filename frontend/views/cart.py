from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.models import User
from decimal import Decimal

from dashboard.models import Product, Order, PartnerPrice, Notification
from user_auth.models import UserProfile
from dashboard.utils import get_algeria_locations, notify_user, resolve_price


CART_SESSION_KEY = "cart"


def _get_cart(request):
    return request.session.setdefault(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _cart_total_items(cart):
    return sum(item["quantity"] for item in cart.values())


def _resolve_for_cart(request, product):
    """Resolve price for the current request context — uses affiliate retail price if referred."""
    affiliate_code = request.session.get("affiliate_code")
    if affiliate_code:
        try:
            aff_profile = UserProfile.objects.get(affiliate_code=affiliate_code, is_approved=True)
            pp = PartnerPrice.objects.filter(
                product=product, buyer=aff_profile.user, is_active=True
            ).first()
            if pp and pp.retail_price is not None:
                return pp.retail_price
        except UserProfile.DoesNotExist:
            pass
    seller_user = product.user or User.objects.filter(is_superuser=True).first()
    buyer_user = request.user if request.user.is_authenticated else None
    return resolve_price(product, seller_user, buyer_user)


def _cart_total_price(cart):
    total = 0
    for item_data in cart.values():
        product = Product.objects.filter(pk=item_data["product_id"]).first()
        if product:
            price = item_data.get("resolved_price") or product.loft_retail_price or 0
            total += float(price) * item_data["quantity"]
    return total


def _get_cart_items_data(request):
    cart = _get_cart(request)
    items = []
    for item_data in cart.values():
        product = Product.objects.filter(pk=item_data["product_id"]).first()
        if not product:
            continue
        price = item_data.get("resolved_price") or product.loft_retail_price or "0"
        subtotal = float(price) * item_data["quantity"]
        items.append({
            "id": item_data["product_id"],
            "product_id": product.pk,
            "product": product,
            "title": product.title,
            "price": str(price),
            "quantity": item_data["quantity"],
            "subtotal": subtotal,
            "subtotal_str": f"{subtotal:.0f}",
            "thumbnail": product.thumbnail.url if product.thumbnail else "",
        })
    return items


@require_POST
def cart_add(request):
    product_id = request.POST.get("product_id")
    quantity = int(request.POST.get("quantity", 1))

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if quantity < 1:
        return JsonResponse({"success": False, "message": _("Invalid quantity.")})

    # Resolve price before adding
    resolved = _resolve_for_cart(request, product)
    if resolved is None:
        return JsonResponse({
            "success": False,
            "message": _("Price not configured for this product. Please contact support.")
        })

    cart = _get_cart(request)
    key = str(product_id)

    if key in cart:
        cart[key]["quantity"] += quantity
        # Refresh the affiliate code in case it changed since first add
        session_code = request.session.get("affiliate_code", "")
        if session_code:
            cart[key]["affiliate_code"] = session_code
    else:
        cart[key] = {
            "product_id": product.pk,
            "quantity": quantity,
            "resolved_price": str(resolved),
            "affiliate_code": request.session.get("affiliate_code", ""),
        }

    _save_cart(request, cart)

    return JsonResponse({
        "success": True,
        "message": _("%(title)s added to cart.") % {"title": product.title},
        "cart_total": _cart_total_items(cart),
        "cart_total_price": str(_cart_total_price(cart)),
    })


@require_POST
def cart_update(request):
    item_id = request.POST.get("item_id")
    quantity = int(request.POST.get("quantity", 1))

    cart = _get_cart(request)
    key = str(item_id)

    if key not in cart:
        return JsonResponse({"success": False, "message": _("Item not found.")})

    if quantity < 1:
        del cart[key]
        _save_cart(request, cart)
        return JsonResponse({
            "success": True,
            "message": _("Item removed."),
            "cart_total": _cart_total_items(cart),
            "cart_total_price": str(_cart_total_price(cart)),
            "removed": True,
        })

    cart[key]["quantity"] = quantity
    _save_cart(request, cart)

    cart_item = cart.get(key, {})
    unit_price = Decimal(str(cart_item.get("resolved_price", 0))) or Decimal("0")
    item_subtotal = unit_price * quantity

    return JsonResponse({
        "success": True,
        "message": _("Cart updated."),
        "cart_total": _cart_total_items(cart),
        "cart_total_price": str(_cart_total_price(cart)),
        "item_subtotal": str(item_subtotal),
    })


@require_POST
def cart_remove(request):
    item_id = request.POST.get("item_id")
    cart = _get_cart(request)
    key = str(item_id)

    if key in cart:
        del cart[key]
        _save_cart(request, cart)

    return JsonResponse({
        "success": True,
        "message": _("Item removed from cart."),
        "cart_total": _cart_total_items(cart),
        "cart_total_price": str(_cart_total_price(cart)),
    })


def cart_load(request):
    cart = _get_cart(request)
    items = []
    for item_data in cart.values():
        product = Product.objects.filter(pk=item_data["product_id"]).first()
        if not product:
            continue
        price = item_data.get("resolved_price") or product.loft_retail_price or "0"
        subtotal = float(price) * item_data["quantity"]
        items.append({
            "id": item_data["product_id"],
            "product_id": product.pk,
            "title": product.title,
            "price": str(price),
            "quantity": item_data["quantity"],
            "subtotal": str(subtotal),
            "thumbnail": product.thumbnail.url if product.thumbnail else "",
            "url": product.get_absolute_url() if hasattr(product, "get_absolute_url") else "#",
        })

    return JsonResponse({
        "success": True,
        "items": items,
        "total_items": _cart_total_items(cart),
        "total_price": str(_cart_total_price(cart)),
    })


def cart_view(request):
    cart = _get_cart(request)
    items_data = _get_cart_items_data(request)
    return render(request, "cart/cart.html", {
        "items": items_data,
        "cart_total_items": _cart_total_items(cart),
        "cart_total_price": _cart_total_price(cart),
    })


def cart_checkout(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("frontend:cart")

    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        wilaya = request.POST.get("wilaya")
        commune = request.POST.get("commune")
        address = request.POST.get("address")

        with transaction.atomic():
            order_items = []
            product_titles = []

            for item_data in list(cart.values()):
                product = Product.objects.filter(pk=item_data["product_id"]).first()
                if not product:
                    continue

                price = item_data.get("resolved_price") or str(product.loft_retail_price or "")
                order_items.append({
                    "product_id": product.pk,
                    "title": product.title,
                    "price": price,
                    "quantity": item_data["quantity"],
                    "thumbnail": product.thumbnail.url if product.thumbnail else "",
                })
                product_titles.append(product.title)

                product.quantity -= item_data["quantity"]
                product.save()

            if not order_items:
                return JsonResponse({"success": False, "errors": [_("No valid items in cart.")]})

            referred_by = request.session.get("affiliate_code", "")

            Order.objects.create(
                items=order_items,
                customer_name=name,
                customer_phone=phone,
                customer_address=address,
                wilaya=wilaya,
                commune=commune,
                referred_by=referred_by,
            )

            admins = User.objects.filter(is_superuser=True)
            for admin in admins:
                notify_user(
                    admin,
                    _("New Order!"),
                    _("New order for %(products)s by %(name)s") % {
                        "products": ", ".join(product_titles),
                        "name": name
                    },
                    link="/dashboard/orders/"
                )

            if referred_by:
                try:
                    aff_profile = UserProfile.objects.get(affiliate_code=referred_by, is_approved=True)
                    notify_user(
                        user=aff_profile.user,
                        title=_("New Order via Your Store"),
                        message=_("%(name)s placed an order for %(products)s through your store.")
                        % {"name": name, "products": ", ".join(product_titles)},
                        notification_type=Notification.NotificationType.INFO,
                        link="/dashboard/orders/",
                    )
                    if aff_profile.role == UserProfile.roleChoices.SEMI_AFFILIATE and aff_profile.parent_affiliate:
                        notify_user(
                            user=aff_profile.parent_affiliate.user,
                            title=_("New Order via Semi-Affiliate"),
                            message=_("%(name)s placed an order for %(products)s through %(semi)s's store.")
                            % {"name": name, "products": ", ".join(product_titles), "semi": aff_profile.user.get_full_name() or aff_profile.user.username},
                            notification_type=Notification.NotificationType.INFO,
                            link="/dashboard/orders/",
                        )
                except UserProfile.DoesNotExist:
                    pass

            request.session[CART_SESSION_KEY] = {}
            request.session.pop("affiliate_code", None)
            request.session.modified = True

        messages.success(request, _("Order placed successfully!"))
        return redirect("frontend:home")

    items_data = _get_cart_items_data(request)
    wilaya_options, communes_data = get_algeria_locations()
    return render(request, "cart/checkout.html", {
        "cart_items": items_data,
        "cart_total_price": _cart_total_price(cart),
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
    })
