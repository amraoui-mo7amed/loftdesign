from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.models import User
from decimal import Decimal

from dashboard.models import Product, ProductItem, Order, PartnerPrice, Notification
from user_auth.models import UserProfile
from dashboard.utils import get_algeria_locations, notify_user, resolve_price, check_low_stock, check_low_stock_product_item
from frontend.checkout import CheckoutError, create_customer_order, validate_customer
from frontend.pricing import customer_price, visitor_currency


CART_SESSION_KEY = "cart"


def _get_cart(request):
    return request.session.setdefault(CART_SESSION_KEY, {})


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _cart_total_items(cart):
    return sum(item["quantity"] for item in cart.values())


def _resolve_for_cart(request, product):
    """Price for the current visitor (affiliate link, professional account, public)."""
    return customer_price(request, product)["dzd"]


def _cart_total_price(cart):
    total = Decimal("0")
    for item_data in cart.values():
        total += Decimal(str(item_data.get("resolved_price") or 0)) * item_data["quantity"]
    return total


def _cart_in_eur(request, cart):
    """True when the visitor is abroad and every cart line has a euro price."""
    return bool(cart) and visitor_currency(request) == "EUR" and all(i.get("price_eur") for i in cart.values())


def _fmt(request, cart, dzd, eur):
    if _cart_in_eur(request, cart) and eur is not None:
        return f"{Decimal(eur):,.2f}".replace(",", "\u202f").replace(".", ",") + " €"
    return f"{Decimal(dzd):,.0f}".replace(",", "\u202f") + " DZD"


def _cart_totals(request, cart):
    dzd = _cart_total_price(cart)
    eur = sum((Decimal(i["price_eur"]) * i["quantity"] for i in cart.values() if i.get("price_eur")), Decimal("0"))
    return {
        "cart_total": _cart_total_items(cart),
        "cart_total_price": str(dzd),
        "cart_total_display": _fmt(request, cart, dzd, eur),
    }


def _get_cart_items_data(request):
    cart = _get_cart(request)
    items = []
    for item_data in cart.values():
        product = Product.objects.filter(pk=item_data["product_id"]).first()
        if not product:
            continue
        price = item_data.get("resolved_price") or product.loft_retail_price or "0"
        subtotal = Decimal(str(price)) * item_data["quantity"]
        eur = Decimal(item_data["price_eur"]) if item_data.get("price_eur") else None
        display_title = product.title
        display_thumbnail = product.thumbnail.url if product.thumbnail else ""
        available_variants = []
        if item_data.get("item_id"):
            display_title += f" — {item_data.get('item_name', '')}"
            if item_data.get("item_thumbnail"):
                display_thumbnail = item_data["item_thumbnail"]
            variants = ProductItem.objects.filter(product=product, is_active=True)
            for v in variants:
                available_variants.append({
                    "id": v.pk,
                    "name": v.name,
                    "color": v.color or "",
                    "dimensions": v.dimensions or "",
                    "stock_quantity": v.stock_quantity,
                    "thumbnail_url": v.thumbnail.url if v.thumbnail else "",
                    "is_selected": str(v.pk) == str(item_data["item_id"]),
                    "gallery_images": ",".join([img.image.url for img in v.gallery_images.all()]),
                })
        items.append({
            "id": item_data.get("item_id") or item_data["product_id"],
            "product_id": product.pk,
            "product": product,
            "title": display_title,
            "price": str(price),
            "quantity": item_data["quantity"],
            "subtotal": subtotal,
            "subtotal_str": f"{subtotal:.0f}",
            "price_display": _fmt(request, cart, price, eur),
            "subtotal_display": _fmt(request, cart, subtotal, eur * item_data["quantity"] if eur is not None else None),
            "thumbnail": display_thumbnail,
            "available_variants": available_variants,
        })
    return items


def add_to_cart(request, product, item, quantity):
    """Add a line to the session cart. Returns None, or the error message."""
    if quantity < 1:
        return _("Invalid quantity.")

    # Check item stock if variant selected
    item_id = item.pk if item else None
    product_id = product.pk
    if item:
        if item.stock_quantity < quantity:
            return _("Requested quantity exceeds available stock for this variant.")

    else:
        in_cart = _get_cart(request).get(str(product_id), {}).get("quantity", 0)
        if product.quantity < quantity + in_cart:
            return _("Only %(stock)s available for this product.") % {"stock": product.quantity}

    # Resolve price before adding
    resolved = _resolve_for_cart(request, product)
    if resolved is None:
        return _("Price not configured for this product. Please contact support.")

    cart = _get_cart(request)
    key = str(item_id) if item_id else str(product_id)

    if key in cart:
        cart[key]["quantity"] += quantity
        cart[key]["resolved_price"] = str(resolved)
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
        if item:
            cart[key]["item_id"] = item.pk
            cart[key]["item_name"] = item.name
            cart[key]["item_thumbnail"] = item.thumbnail.url if item.thumbnail else ""
    cart[key]["price_eur"] = str(product.price_eur) if product.price_eur else ""

    _save_cart(request, cart)
    return None


@require_POST
def cart_add(request):
    product_id = request.POST.get("product_id")
    item_id = request.POST.get("item_id")
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "message": _("Invalid quantity.")})

    product = get_object_or_404(Product, pk=product_id, is_active=True, status=Product.ProductStatus.APPROVED)
    item = get_object_or_404(ProductItem, pk=item_id, product=product, is_active=True) if item_id else None
    error = add_to_cart(request, product, item, quantity)
    if error:
        return JsonResponse({"success": False, "message": error})
    cart = _get_cart(request)

    return JsonResponse({
        "success": True,
        "message": _("%(title)s added to cart.") % {"title": product.title},
        **_cart_totals(request, cart),
    })


@require_POST
def cart_switch_variant(request):
    old_item_id = request.POST.get("old_item_id")
    new_item_id = request.POST.get("new_item_id")

    if not old_item_id or not new_item_id:
        return JsonResponse({"success": False, "message": _("Missing variant IDs.")})

    cart = _get_cart(request)
    old_key = str(old_item_id)

    if old_key not in cart:
        return JsonResponse({"success": False, "message": _("Item not found in cart.")})

    entry = cart[old_key]
    new_variant = get_object_or_404(ProductItem, pk=new_item_id, product_id=entry["product_id"], is_active=True)
    if new_variant.stock_quantity < 1:
        return JsonResponse({"success": False, "message": _("This variant is out of stock.")})

    new_key = str(new_item_id)
    entry["item_id"] = new_variant.pk
    entry["item_name"] = new_variant.name
    entry["item_thumbnail"] = new_variant.thumbnail.url if new_variant.thumbnail else ""

    if old_key != new_key:
        cart[new_key] = entry
        del cart[old_key]

    _save_cart(request, cart)

    new_quantity = entry["quantity"]
    unit_price = Decimal(str(entry.get("resolved_price", 0))) or Decimal("0")
    item_subtotal = unit_price * new_quantity

    items_data = _get_cart_items_data(request)
    updated_item = next((i for i in items_data if str(i["id"]) == str(new_item_id)), None)
    if updated_item:
        updated_item = {k: (str(v) if isinstance(v, Decimal) else v) for k, v in updated_item.items() if k != "product"}

    return JsonResponse({
        "success": True,
        "message": _("Variant changed to %(name)s.") % {"name": new_variant.name},
        "item": updated_item,
        **_cart_totals(request, cart),
        "item_subtotal": str(item_subtotal),
        "item_subtotal_display": updated_item["subtotal_display"] if updated_item else "",
    })


@require_POST
def cart_update(request):
    item_id = request.POST.get("item_id")
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "message": _("Invalid quantity.")})

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
            **_cart_totals(request, cart),
            "removed": True,
        })

    # Re-check stock when increasing quantity for variant items
    entry = cart[key]
    if entry.get("item_id") and quantity > entry["quantity"]:
        variant = ProductItem.objects.filter(pk=entry["item_id"]).first()
        if variant and variant.stock_quantity < quantity:
            return JsonResponse({
                "success": False,
                "message": _(
                    "Only %(stock)s available for this variant."
                ) % {"stock": variant.stock_quantity}
            })
    elif quantity > entry["quantity"]:
        product = Product.objects.filter(pk=entry["product_id"]).first()
        if product and product.quantity < quantity:
            return JsonResponse({
                "success": False,
                "message": _("Only %(stock)s available for this product.") % {"stock": product.quantity}
            })

    cart[key]["quantity"] = quantity
    _save_cart(request, cart)

    cart_item = cart.get(key, {})
    unit_price = Decimal(str(cart_item.get("resolved_price", 0))) or Decimal("0")
    item_subtotal = unit_price * quantity

    eur = Decimal(cart_item["price_eur"]) * quantity if cart_item.get("price_eur") else None
    return JsonResponse({
        "success": True,
        "message": _("Cart updated."),
        **_cart_totals(request, cart),
        "item_subtotal": str(item_subtotal),
        "item_subtotal_display": _fmt(request, cart, item_subtotal, eur),
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
        **_cart_totals(request, cart),
    })


def cart_load(request):
    cart = _get_cart(request)
    items = []
    for item_data in cart.values():
        product = Product.objects.filter(pk=item_data["product_id"]).first()
        if not product:
            continue
        price = item_data.get("resolved_price") or product.loft_retail_price or "0"
        subtotal = Decimal(str(price)) * item_data["quantity"]
        eur = Decimal(item_data["price_eur"]) if item_data.get("price_eur") else None
        display_title = product.title
        display_thumbnail = product.thumbnail.url if product.thumbnail else ""
        if item_data.get("item_id"):
            display_title += f" — {item_data.get('item_name', '')}"
            if item_data.get("item_thumbnail"):
                display_thumbnail = item_data["item_thumbnail"]
        items.append({
            "id": item_data.get("item_id") or item_data["product_id"],
            "product_id": product.pk,
            "title": display_title,
            "price": str(price),
            "quantity": item_data["quantity"],
            "subtotal": str(subtotal),
            "price_display": _fmt(request, cart, price, eur),
            "thumbnail": display_thumbnail,
            "url": product.get_absolute_url() if hasattr(product, "get_absolute_url") else "#",
        })

    return JsonResponse({
        "success": True,
        "items": items,
        "total_items": _cart_total_items(cart),
        "total_price": str(_cart_total_price(cart)),
        "total_display": _cart_totals(request, cart)["cart_total_display"],
    })


def cart_view(request):
    cart = _get_cart(request)
    items_data = _get_cart_items_data(request)
    return render(request, "cart/cart.html", {
        "items": items_data,
        "cart_total_items": _cart_total_items(cart),
        "cart_total_price": _cart_total_price(cart),
        "cart_total_display": _cart_totals(request, cart)["cart_total_display"],
    })


def cart_checkout(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("frontend:cart")

    # Foreign address form only when the order is really billed in euros.
    foreign = _cart_in_eur(request, cart)
    customer, errors = {}, {}
    if request.method == "POST":
        customer = {k: (request.POST.get(k) or "").strip() for k in ("name", "phone", "address", "wilaya", "commune")}
        errors = validate_customer(customer, foreign)
    if request.method == "POST" and not errors:
        lines = [(i["product_id"], i.get("item_id"), i["quantity"]) for i in cart.values()]
        try:
            order = create_customer_order(request, lines, customer)
        except CheckoutError as e:
            messages.error(request, str(e))
            return redirect("frontend:cart")
        name = customer["name"]
        product_titles = [i["title"] for i in order.items]
        referred_by = order.referred_by
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

        request.session["last_order_id"] = order.pk
        return redirect("frontend:order_success")

    items_data = _get_cart_items_data(request)
    wilaya_options, communes_data = get_algeria_locations()
    return render(request, "cart/checkout.html", {
        "cart_items": items_data,
        "cart_total_price": _cart_total_price(cart),
        "cart_total_display": _cart_totals(request, cart)["cart_total_display"],
        "foreign": foreign,
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
        "customer": customer,
        "errors": errors,
    }, status=400 if errors else 200)


def order_success(request):
    """Confirmation page shown once after checkout (order kept in the session)."""
    from dashboard.models import Order

    order = None
    order_id = request.session.get("last_order_id")
    if order_id:
        order = Order.objects.filter(pk=order_id).first()
    if order is None:
        return redirect("frontend:home")
    return render(request, "cart/order_success.html", {"order": order})
