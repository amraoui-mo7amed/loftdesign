from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from dashboard.models import Portfolio, Product, Category, Order
from django.contrib.auth.models import User
from django.db.models import Sum, Count
import json


@login_required
def dash_home(request):
    user_profile = getattr(request.user, "profile", None)
    is_admin = request.user.is_superuser or (
        user_profile and user_profile.role == UserProfile.roleChoices.ADMIN
    )
    role = "admin" if is_admin else "provider"

    if is_admin:
        total_providers = UserProfile.objects.filter(
            role=UserProfile.roleChoices.PROVIDER
        ).count()
        total_portfolios = Portfolio.objects.count()
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(
            status=Order.OrderStatus.PENDING
        ).count()
        pending_affiliates = UserProfile.objects.filter(
            role=UserProfile.roleChoices.AFFILIATE, is_approved=False
        ).count()
        pending_products = Product.objects.filter(
            status=Product.ProductStatus.PENDING
        ).count()

        recent_items = list(Order.objects.order_by("-created_at")[:5])

        context = {
            "role": role,
            "stat_1": {
                "title": _("Total Providers"),
                "value": total_providers,
                "icon": "fa-users",
                "color": "primary",
                "trend": "+2",
            },
            "stat_2": {
                "title": _("Pending Products"),
                "value": pending_products,
                "icon": "fa-clock",
                "color": "warning",
                "trend": str(pending_products),
                "trend_dir": "up",
                "trend_color": "warning",
                "link": "dash:product_pending_list",
            },
            "stat_3": {
                "title": _("Total Orders"),
                "value": total_orders,
                "icon": "fa-shopping-cart",
                "color": "primary",
                "trend": str(pending_orders),
                "trend_dir": "down",
                "trend_color": "danger",
            },
            "stat_4": {
                "title": _("Pending Affiliates"),
                "value": pending_affiliates,
                "icon": "fa-handshake",
                "color": "info",
            },
            "chart_title": _("Portfolio Distribution"),
            "user_dist_labels": json.dumps(
                [str(_("Providers")), str(_("Projects")), str(_("Orders"))]
            ),
            "user_dist_values": json.dumps(
                [total_providers, total_portfolios, total_orders]
            ),
            "list_title": _("Recent Orders"),
            "recent_items": recent_items,
        }
    else:
        my_products = Product.objects.filter(user=request.user).count()
        my_active = Product.objects.filter(
            user=request.user, is_active=True
        ).count()

        user_product_ids = set(
            Product.objects.filter(user=request.user).values_list("id", flat=True)
        )
        all_orders = Order.objects.all().order_by("-created_at")
        provider_orders = [
            o for o in all_orders
            if any(item.get("product_id") in user_product_ids for item in o.items)
        ]
        my_orders = len(provider_orders)
        my_pending = sum(1 for o in provider_orders if o.status == Order.OrderStatus.PENDING)
        my_completed = sum(1 for o in provider_orders if o.status == Order.OrderStatus.COMPLETED)
        recent_items = provider_orders[:5]

        context = {
            "role": role,
            "stat_1": {
                "title": _("My Products"),
                "value": my_products,
                "icon": "fa-box-open",
                "color": "primary",
                "trend": "+{}".format(my_products),
            },
            "stat_2": {
                "title": _("Active"),
                "value": my_active,
                "icon": "fa-check-circle",
                "color": "success",
                "trend": "+{}".format(my_active),
            },
            "stat_3": {
                "title": _("Total Orders"),
                "value": my_orders,
                "icon": "fa-shopping-cart",
                "color": "warning",
                "trend": str(my_pending),
                "trend_dir": "down",
                "trend_color": "danger",
            },
            "stat_4": {
                "title": _("Completed"),
                "value": my_completed,
                "icon": "fa-flag-checkered",
                "color": "info",
            },
            "chart_title": _("Weekly Orders"),
            "chart_values": json.dumps([my_pending, my_completed, my_orders]),
            "list_title": _("My Recent Orders"),
            "recent_items": recent_items,
            "list_items": [],
        }

    return render(request, "dash/dash_home.html", context)
