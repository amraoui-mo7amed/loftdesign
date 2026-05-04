from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from dashboard.models import Portfolio, Product, Category, Order
from django.contrib.auth.models import User
import json


@login_required
def dash_home(request):
    user_profile = getattr(request.user, "profile", None)

    # Core Statistics
    total_portfolios = Portfolio.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status=Order.OrderStatus.PENDING).count()

    context = {
        "role": "admin" if request.user.is_superuser else "user",
        "stat_1": {
            "title": _("Total Projects"),
            "value": total_portfolios,
            "icon": "fa-briefcase",
            "color": "primary",
        },
        "stat_2": {
            "title": _("Total Products"),
            "value": total_products,
            "icon": "fa-box-open",
            "color": "success",
        },
        "stat_3": {
            "title": _("Total Leads"),
            "value": total_orders,
            "icon": "fa-shopping-cart",
            "color": "warning",
        },
        "stat_4": {
            "title": _("Pending Leads"),
            "value": pending_orders,
            "icon": "fa-clock",
            "color": "info",
        },
    }

    if request.user.is_superuser:
        # Admin List: Recent Orders
        context.update(
            {
                "chart_title": _("Portfolio Distribution"),
                "user_dist_labels": json.dumps(
                    [str(_("Projects")), str(_("Products")), str(_("Total Leads"))]
                ),
                "user_dist_values": json.dumps(
                    [total_portfolios, total_products, total_orders]
                ),
                "list_title": _("Recent Leads"),
                "recent_orders": Order.objects.select_related("product").order_by(
                    "-created_at"
                )[:5],
            }
        )
    else:
        # User Specific List (Placeholder for now as users don't own objects yet)
        context.update(
            {
                "chart_title": _("Lead Activity"),
                "chart_values": json.dumps([5, 8, 4, 12, 10, 15, total_orders]),
                "list_title": _("Recent Activity"),
                "list_items": [
                    _("System stabilized"),
                    _("Dashboard synchronized"),
                ],
            }
        )

    return render(request, "dash/dash_home.html", context)
