CART_SESSION_KEY = "cart"


def cart_context(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    cart_count = sum(item["quantity"] for item in cart.values())
    return {
        "cart_count": cart_count,
    }
