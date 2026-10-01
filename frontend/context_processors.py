import os
import time

CART_SESSION_KEY = "cart"
# Cache-busting token for CSS/JS: fixed for the life of the process (changes on
# each deploy/restart) instead of a new value on every page view.
ASSET_VERSION = os.environ.get("ASSET_VERSION") or str(int(time.time()))


def cart_context(request):
    cart = request.session.get(CART_SESSION_KEY, {})
    cart_count = sum(item["quantity"] for item in cart.values())
    from frontend.pricing import visitor_currency

    return {
        "cart_count": cart_count,
        "affiliate_code": request.session.get("affiliate_code", ""),
        "store_currency": visitor_currency(request),
        "ASSET_VERSION": ASSET_VERSION,
    }
