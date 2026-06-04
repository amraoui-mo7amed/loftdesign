from dashboard.models import Cart


def cart_context(request):
    """Add cart count and cart URL to all templates."""
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        cart = Cart.objects.filter(session_key=session_key).first() if session_key else None

    if cart:
        cart_count = cart.total_items()

    return {
        "cart_count": cart_count,
    }
