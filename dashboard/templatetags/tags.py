from django import template
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from dashboard.models import Portfolio, Product, Order

register = template.Library()

@register.inclusion_tag("components/pagination.html", takes_context=True)
def render_pagination(context, page_obj):
    request = context["request"]
    querydict = request.GET.copy()
    if "page" in querydict:
        querydict.pop("page")

    base_url = request.path + "?" + querydict.urlencode()
    if base_url and not base_url.endswith("&") and not base_url.endswith("?"):
        base_url += "&"

    return {
        "page_obj": page_obj,
        "base_url": base_url,
    }



@register.inclusion_tag("components/dashboard_stats.html", takes_context=True)
def dashboard_stats(context):
    request = context["request"]
    if not request.user.is_authenticated:
        return {"stats": []}

    profile = getattr(request.user, "profile", None)
    role = profile.role if profile else None
    is_admin = request.user.is_superuser or role == "admin"

    stats = []

    if is_admin:
        pending_orders = Order.objects.filter(status=Order.OrderStatus.PENDING).count()
        pending_affiliates = UserProfile.objects.filter(role=UserProfile.roleChoices.AFFILIATE, is_approved=False).count()
        stats = [
            {"title": _("Providers"), "value": UserProfile.objects.filter(role=UserProfile.roleChoices.PROVIDER).count(), "icon": "fa-users", "color": "primary"},
            {"title": _("Products"), "value": Product.objects.count(), "icon": "fa-box-open", "color": "success"},
            {"title": _("Affiliates Pending"), "value": pending_affiliates, "icon": "fa-handshake", "color": "info"},
            {"title": _("Pending Orders"), "value": pending_orders, "icon": "fa-clock", "color": "warning"},
        ]
    elif role == "provider":
        user_products = Product.objects.filter(user=request.user)
        user_product_ids = set(user_products.values_list("id", flat=True))
        all_orders = Order.objects.all()
        my_order_count = sum(
            1 for o in all_orders
            if any(item.get("product_id") in user_product_ids for item in o.items)
        )
        stats = [
            {"title": _("My Products"), "value": user_products.count(), "icon": "fa-box-open", "color": "success"},
            {"title": _("Portfolios"), "value": Portfolio.objects.count(), "icon": "fa-briefcase", "color": "warning"},
            {"title": _("My Orders"), "value": my_order_count, "icon": "fa-shopping-cart", "color": "primary"},
            {"title": _("Commission"), "value": f"{profile.commission}%", "icon": "fa-percentage", "color": "info"},
        ]

    return {"stats": stats}


@register.filter
def humanize_number(value):
    """
    Converts a large number into a human-readable format with k, M, B, etc.
    Example:
        1500 -> 1.5k
        2500000 -> 2.5M
    """
    try:
        num = float(value)
    except (ValueError, TypeError):
        return value

    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}k"
    else:
        return f"{num:.0f}"
