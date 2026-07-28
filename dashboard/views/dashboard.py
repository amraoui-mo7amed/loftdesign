from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from dashboard.models import Product, Order, PartnerPrice
from django.contrib.auth.models import User
from django.db.models import Sum, Count
import json
from decimal import Decimal


@login_required
def dash_home(request):
    user_profile = getattr(request.user, "profile", None)
    is_admin = request.user.is_superuser or (
        user_profile and user_profile.role == UserProfile.roleChoices.ADMIN
    )
    role = user_profile.role if user_profile else "provider"

    if is_admin or role == "admin":
        total_providers = UserProfile.objects.filter(
            role=UserProfile.roleChoices.PROVIDER
        ).count()
        total_affiliates = UserProfile.objects.filter(
            role=UserProfile.roleChoices.AFFILIATE, is_approved=True
        ).count()
        total_semi = UserProfile.objects.filter(
            role=UserProfile.roleChoices.SEMI_AFFILIATE, is_approved=True
        ).count()
        total_orders = Order.objects.count()
        delivered_orders = Order.objects.filter(
            status=Order.OrderStatus.DELIVERED
        ).count()
        pending_orders = Order.objects.filter(
            status=Order.OrderStatus.PENDING
        ).count()
        pending_affiliates = UserProfile.objects.filter(
            role=UserProfile.roleChoices.AFFILIATE, is_approved=False
        ).count()
        pending_products = Product.objects.filter(
            status=Product.ProductStatus.PENDING
        ).count()

        # Revenue
        total_revenue = sum(
            o.total_price() for o in Order.objects.filter(status=Order.OrderStatus.DELIVERED)
        )

        recent_items = list(Order.objects.order_by("-created_at")[:5])

        context = {
            "role": role,
            "stat_1": {
                "title": _("Total Providers"),
                "value": total_providers,
                "icon": "fa-users",
                "color": "primary",
            },
            "stat_2": {
                "title": _("Total Affiliates"),
                "value": total_affiliates,
                "icon": "fa-handshake",
                "color": "success",
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
                "title": _("Delivered"),
                "value": delivered_orders,
                "icon": "fa-check-circle",
                "color": "success",
            },
            "stat_5": {
                "title": _("Revenue (DZD)"),
                "value": f"{total_revenue:,.0f}",
                "icon": "fa-dollar-sign",
                "color": "warning",
            },
            "stat_6": {
                "title": _("Pending Products"),
                "value": pending_products,
                "icon": "fa-clock",
                "color": "warning",
            },
            "chart_title": _("User Distribution"),
            "user_dist_labels": json.dumps(
                [str(_("Providers")), str(_("Affiliates")), str(_("Semi-Affiliates"))]
            ),
            "user_dist_values": json.dumps(
                [total_providers, total_affiliates, total_semi]
            ),
            "list_title": _("Recent Orders"),
            "recent_items": recent_items,
        }
    elif role == UserProfile.roleChoices.AFFILIATE:
        # Affiliate dashboard
        profile = user_profile
        referred_codes = [profile.affiliate_code] if profile.affiliate_code else []
        if profile and profile.affiliate_code:
            semi_codes = UserProfile.objects.filter(
                parent_affiliate=profile, is_approved=True
            ).exclude(affiliate_code__isnull=True).values_list("affiliate_code", flat=True)
            referred_codes.extend(semi_codes)

        my_orders_qs = Order.objects.filter(referred_by__in=referred_codes).order_by("-created_at")
        total_orders = my_orders_qs.count()
        pending_orders = my_orders_qs.filter(status=Order.OrderStatus.PENDING).count()
        delivered_orders = my_orders_qs.filter(status=Order.OrderStatus.DELIVERED).count()
        catalog_count = PartnerPrice.objects.filter(buyer=request.user, is_active=True).count()
        semi_count = UserProfile.objects.filter(parent_affiliate=profile, is_approved=True).count()

        recent_items = list(my_orders_qs[:5])

        context = {
            "role": role,
            "stat_1": {
                "title": _("Total Orders"),
                "value": total_orders,
                "icon": "fa-shopping-cart",
                "color": "primary",
            },
            "stat_2": {
                "title": _("Pending"),
                "value": pending_orders,
                "icon": "fa-clock",
                "color": "warning",
            },
            "stat_3": {
                "title": _("Delivered"),
                "value": delivered_orders,
                "icon": "fa-check-circle",
                "color": "success",
            },
            "stat_4": {
                "title": _("Catalog Items"),
                "value": catalog_count,
                "icon": "fa-boxes",
                "color": "info",
            },
            "stat_5": {
                "title": _("Semi-Affiliates"),
                "value": semi_count,
                "icon": "fa-user-friends",
                "color": "secondary",
            },
            "chart_title": _("Order Status"),
            "chart_values": json.dumps([pending_orders, delivered_orders]),
            "chart_labels": json.dumps([str(_("Pending")), str(_("Delivered"))]),
            "list_title": _("Recent Orders"),
            "recent_items": recent_items,
        }
    elif role == UserProfile.roleChoices.SEMI_AFFILIATE:
        profile = user_profile
        referred_codes = [profile.affiliate_code] if profile.affiliate_code else []

        my_orders_qs = Order.objects.filter(referred_by__in=referred_codes).order_by("-created_at")
        total_orders = my_orders_qs.count()
        pending_orders = my_orders_qs.filter(status=Order.OrderStatus.PENDING).count()
        delivered_orders = my_orders_qs.filter(status=Order.OrderStatus.DELIVERED).count()
        catalog_count = PartnerPrice.objects.filter(buyer=request.user, is_active=True).count()

        recent_items = list(my_orders_qs[:5])

        context = {
            "role": role,
            "stat_1": {
                "title": _("Total Orders"),
                "value": total_orders,
                "icon": "fa-shopping-cart",
                "color": "primary",
            },
            "stat_2": {
                "title": _("Pending"),
                "value": pending_orders,
                "icon": "fa-clock",
                "color": "warning",
            },
            "stat_3": {
                "title": _("Delivered"),
                "value": delivered_orders,
                "icon": "fa-check-circle",
                "color": "success",
            },
            "stat_4": {
                "title": _("Catalog Items"),
                "value": catalog_count,
                "icon": "fa-boxes",
                "color": "info",
            },
            "chart_title": _("Order Status"),
            "chart_values": json.dumps([pending_orders, delivered_orders]),
            "chart_labels": json.dumps([str(_("Pending")), str(_("Delivered"))]),
            "list_title": _("Recent Orders"),
            "recent_items": recent_items,
        }
    else:
        # Provider dashboard
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
        my_delivered = sum(1 for o in provider_orders if o.status == Order.OrderStatus.DELIVERED)
        my_fulfilling = sum(1 for o in provider_orders if o.status in [
            Order.OrderStatus.ADMIN_VALIDATED, Order.OrderStatus.SUPPLIER_FULFILLING
        ])
        recent_items = provider_orders[:5]

        context = {
            "role": role,
            "stat_1": {
                "title": _("My Products"),
                "value": my_products,
                "icon": "fa-box-open",
                "color": "primary",
            },
            "stat_2": {
                "title": _("Active"),
                "value": my_active,
                "icon": "fa-check-circle",
                "color": "success",
            },
            "stat_3": {
                "title": _("Total Orders"),
                "value": my_orders,
                "icon": "fa-shopping-cart",
                "color": "warning",
            },
            "stat_4": {
                "title": _("To Fulfill"),
                "value": my_fulfilling,
                "icon": "fa-truck",
                "color": "info",
            },
            "stat_5": {
                "title": _("Delivered"),
                "value": my_delivered,
                "icon": "fa-flag-checkered",
                "color": "success",
            },
            "chart_title": _("Order Status"),
            "chart_values": json.dumps([my_pending, my_fulfilling, my_delivered]),
            "chart_labels": json.dumps([str(_("Pending")), str(_("Fulfilling")), str(_("Delivered"))]),
            "list_title": _("My Recent Orders"),
            "recent_items": recent_items,
        }

    return render(request, "dash/dash_home.html", context)
