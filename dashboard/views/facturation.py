from django.shortcuts import render, get_object_or_404
from decimal import Decimal
from django.utils.translation import gettext as _
from django.db.models import Q

from dashboard.decorator import role_required
from dashboard.models import Order, LoftPrice
from user_auth.models import UserProfile


_RC = UserProfile.roleChoices


def _commission_for_order(order):
    """Compute total commission for a single DELIVERED order."""
    total = Decimal("0.00")
    for item in order.items:
        product_id = item.get("product_id")
        price = Decimal(str(item.get("price", 0))) or Decimal("0")
        quantity = int(item.get("quantity", 1))
        if product_id:
            try:
                lp = LoftPrice.objects.get(product_id=product_id)
                margin = price - lp.loft_default_wholesale_price
                if margin > 0:
                    total += margin * quantity
            except LoftPrice.DoesNotExist:
                pass
    return total


def _compute_user_stats(profile):
    """Compute billing stats for a single user profile."""
    if not profile.affiliate_code:
        return {
            "profile": profile,
            "orders": [],
            "orders_count": 0,
            "total_earned": Decimal("0.00"),
            "total_paid": Decimal("0.00"),
            "total_unpaid": Decimal("0.00"),
        }
    delivered_orders = Order.objects.filter(
        referred_by=profile.affiliate_code,
        status=Order.OrderStatus.DELIVERED,
    ).order_by("-created_at")

    total_earned = Decimal("0.00")
    total_paid = Decimal("0.00")
    orders = []
    for order in delivered_orders:
        commission = _commission_for_order(order)
        total_earned += commission
        if order.commission_paid:
            total_paid += commission
        orders.append({"order": order, "commission": commission})

    return {
        "profile": profile,
        "orders": orders,
        "orders_count": len(orders),
        "total_earned": total_earned,
        "total_paid": total_paid,
        "total_unpaid": total_earned - total_paid,
    }


@role_required(allowed_roles=[_RC.ADMIN, _RC.AFFILIATE, _RC.SEMI_AFFILIATE])
def facturation_list(request):
    """Billing overview — admin sees all+self, affiliate sees self+semi, semi sees self."""
    profile = getattr(request.user, "profile", None)
    role = profile.role if profile else None

    q = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()

    if role == _RC.ADMIN:
        target_profiles = UserProfile.objects.filter(
            role__in=[_RC.AFFILIATE, _RC.SEMI_AFFILIATE],
            is_approved=True,
            affiliate_code__isnull=False,
        ).select_related("user").order_by("user__username")
        # Include admin's own profile
        target_profiles = [profile] + list(target_profiles)
    elif role == _RC.AFFILIATE:
        semi_profiles = UserProfile.objects.filter(
            parent_affiliate=profile, is_approved=True, affiliate_code__isnull=False
        ).select_related("user")
        target_profiles = [profile] + list(semi_profiles)
    elif role == _RC.SEMI_AFFILIATE:
        target_profiles = [profile]
    else:
        target_profiles = []

    # Search filter
    if q:
        filtered = []
        for p in target_profiles:
            name = (p.user.get_full_name() or p.user.username).lower()
            code = (p.affiliate_code or "").lower()
            if q.lower() in name or q.lower() in code:
                filtered.append(p)
        target_profiles = filtered

    # Role filter
    if role_filter and role_filter in [_RC.AFFILIATE, _RC.SEMI_AFFILIATE, _RC.ADMIN]:
        target_profiles = [p for p in target_profiles if p.role == role_filter]

    stats = [_compute_user_stats(p) for p in target_profiles]

    totals = {
        "orders_count": sum(s["orders_count"] for s in stats),
        "total_earned": sum(s["total_earned"] for s in stats),
        "total_paid": sum(s["total_paid"] for s in stats),
        "total_unpaid": sum(s["total_unpaid"] for s in stats),
    }

    role_choices = [
        {"value": "affiliate", "label": _("Affiliate")},
        {"value": "semi_affiliate", "label": _("Semi-Affiliate")},
        {"value": "admin", "label": _("Admin")},
    ]
    selected_role_label = None
    for rc in role_choices:
        if rc["value"] == role_filter:
            selected_role_label = rc["label"]
            break

    return render(request, "facturation/list.html", {
        "stats": stats,
        "totals": totals,
        "q": q,
        "role_filter": role_filter,
        "role_choices": role_choices,
        "selected_role_label": selected_role_label,
        "title": _("Billing"),
    })


@role_required(allowed_roles=[_RC.ADMIN, _RC.AFFILIATE, _RC.SEMI_AFFILIATE])
def facturation_detail(request, profile_id):
    """Billing breakdown for a single user."""
    current_profile = getattr(request.user, "profile", None)
    role = current_profile.role if current_profile else None

    target = get_object_or_404(UserProfile, id=profile_id)

    if role == _RC.SEMI_AFFILIATE and target.id != current_profile.id:
        return render(request, "partials/errorList.html", {
            "error": _("You can only view your own billing."),
        })
    if role == _RC.AFFILIATE:
        if target.id != current_profile.id and target.parent_affiliate_id != current_profile.id:
            return render(request, "partials/errorList.html", {
                "error": _("You can only view your own billing or your semi-affiliates."),
            })

    user_stats = _compute_user_stats(target)

    return render(request, "facturation/detail.html", {
        "target": target,
        "stats": user_stats,
        "title": _("Billing — %(name)s") % {"name": target.user.get_full_name() or target.user.username},
    })
