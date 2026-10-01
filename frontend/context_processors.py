CART_SESSION_KEY = "cart"


def cart_context(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    cart_count = sum(item["quantity"] for item in cart.values())
    from frontend.pricing import visitor_currency

    return {
        "cart_count": cart_count,
        "affiliate_code": request.session.get("affiliate_code", ""),
        "store_currency": visitor_currency(request),
    }
