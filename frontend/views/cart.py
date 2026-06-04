from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.models import User

from dashboard.models import Cart, CartItem, Product, Order
from dashboard.utils import get_algeria_locations, notify_user


def _get_cart(request):
    """Get or create a cart for the current user/session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart


@require_POST
def cart_add(request):
    """Add a product to the cart (AJAX)."""
    product_id = request.POST.get("product_id")
    quantity = int(request.POST.get("quantity", 1))

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if quantity < 1:
        return JsonResponse({"success": False, "message": _("Invalid quantity.")})

    cart = _get_cart(request)
    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
        item.save()

    return JsonResponse({
        "success": True,
        "message": _("%(title)s added to cart.") % {"title": product.title},
        "cart_total": cart.total_items(),
        "cart_total_price": str(cart.total_price()),
    })


@require_POST
def cart_update(request):
    """Update quantity of a cart item (AJAX)."""
    item_id = request.POST.get("item_id")
    quantity = int(request.POST.get("quantity", 1))

    cart = _get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)

    if quantity < 1:
        item.delete()
        return JsonResponse({
            "success": True,
            "message": _("Item removed."),
            "cart_total": cart.total_items(),
            "cart_total_price": str(cart.total_price()),
            "removed": True,
        })

    item.quantity = quantity
    item.save()

    return JsonResponse({
        "success": True,
        "message": _("Cart updated."),
        "cart_total": cart.total_items(),
        "cart_total_price": str(cart.total_price()),
        "item_subtotal": str(item.subtotal()),
    })


@require_POST
def cart_remove(request):
    """Remove an item from the cart (AJAX)."""
    item_id = request.POST.get("item_id")
    cart = _get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()

    return JsonResponse({
        "success": True,
        "message": _("Item removed from cart."),
        "cart_total": cart.total_items(),
        "cart_total_price": str(cart.total_price()),
    })


def cart_load(request):
    """Return cart data as JSON (for drawer)."""
    cart = _get_cart(request)
    items = []
    for item in cart.items.select_related("product").all():
        items.append({
            "id": item.pk,
            "product_id": item.product.pk,
            "title": item.product.title,
            "price": str(item.product.price) if item.product.price else "0",
            "quantity": item.quantity,
            "subtotal": str(item.subtotal()),
            "thumbnail": item.product.thumbnail.url if item.product.thumbnail else "",
            "url": item.product.get_absolute_url() if hasattr(item.product, "get_absolute_url") else "#",
        })

    return JsonResponse({
        "success": True,
        "items": items,
        "total_items": cart.total_items(),
        "total_price": str(cart.total_price()),
    })


def cart_view(request):
    """Full cart page."""
    cart = _get_cart(request)
    items = cart.items.select_related("product").all()
    return render(request, "cart/cart.html", {
        "cart": cart,
        "items": items,
    })


def cart_checkout(request):
    """View to process checkout."""
    cart = _get_cart(request)
    if cart.items.count() == 0:
        return redirect("frontend:cart")

    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        wilaya = request.POST.get("wilaya")
        commune = request.POST.get("commune")
        address = request.POST.get("address")

        with transaction.atomic():
            for item in cart.items.all():
                # Create Order
                Order.objects.create(
                    product=item.product,
                    quantity=item.quantity,
                    customer_name=name,
                    customer_phone=phone,
                    customer_address=address,
                    wilaya=wilaya,
                    commune=commune,
                    status=Order.OrderStatus.PENDING,
                )
                # Deduct stock
                item.product.quantity -= item.quantity
                item.product.save()
                
                # Notify admins
                admins = User.objects.filter(is_superuser=True)
                for admin in admins:
                    notify_user(
                        admin,
                        _("New Order!"),
                        _("New order for %(product)s by %(name)s") % {"product": item.product.title, "name": name},
                        link="/dashboard/orders/"
                    )

            # Clear cart
            cart.items.all().delete()
            
        messages.success(request, _("Order placed successfully!"))
        return redirect("frontend:home")

    # GET request: render checkout page
    wilaya_options, communes_data = get_algeria_locations()
    return render(request, "cart/checkout.html", {
        "cart": cart,
        "wilaya_options": wilaya_options,
        "communes_data": communes_data,
    })
