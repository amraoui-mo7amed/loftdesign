from django.utils.translation import gettext_lazy as _
from functools import lru_cache


@lru_cache(maxsize=128)
def _build_menu(is_authenticated, is_superuser, role, is_trusted=False):
    """
    Build menu from primitive args so lru_cache works (User objects aren't hashable).
    """
    menu = [
        {
            "title": _("Dashboard"),
            "icon": "fas fa-th-large",
            "url_name": "dash:dash_home",
        },
    ]

    if not is_authenticated:
        return menu

    is_admin = is_superuser
    is_affiliate = role == "affiliate"
    is_semi_affiliate = role == "semi_affiliate"

    # Wallet — all business roles
    if is_admin or is_affiliate or is_semi_affiliate or role == "provider":
        menu.append({
            "title": _("Wallet"),
            "icon": "fas fa-wallet",
            "url_name": "dash:wallet_list",
        })

    # Admin only links
    if is_admin:
        menu.append({
            "title": _("Withdrawals"),
            "icon": "fas fa-hand-holding-usd",
            "url_name": "dash:withdrawal_request_list",
        })
        menu.append({
            "title": _("Affiliates"),
            "icon": "fas fa-handshake",
            "url_name": "dash:affiliate_list",
        })
        menu.append({
            "title": _("Semi-Affiliates"),
            "icon": "fas fa-user-friends",
            "url_name": "dash:semi_affiliate_list",
        })
        menu.append({
            "title": _("Providers"),
            "icon": "fas fa-users",
            "url_name": "dash:user_list",
        })
        menu.append({
            "title": _("Portfolio"),
            "icon": "fas fa-briefcase",
            "url_name": "dash:portfolio_list",
        })
        menu.append({
            "title": _("Categories"),
            "icon": "fas fa-tags",
            "url_name": "dash:category_list",
        })
        menu.append({
            "title": _("Contact Leads"),
            "icon": "fas fa-envelope-open-text",
            "url_name": "dash:contact_request_list",
        })

    # Admin, Provider, and Affiliate links
    if is_admin or (role == "provider" and is_trusted):
        menu.append({
            "title": _("Products"),
            "icon": "fas fa-box-open",
            "url_name": "dash:product_list",
        })
        menu.append({
            "title": _("Orders"),
            "icon": "fas fa-shopping-cart",
            "url_name": "dash:order_list",
        })
    elif is_affiliate or is_semi_affiliate:
        menu.append({
            "title": _("Orders"),
            "icon": "fas fa-shopping-cart",
            "url_name": "dash:order_list",
        })

    # Affiliate / Semi-Affiliate links
    if is_affiliate or is_semi_affiliate:
        menu.append({
            "title": _("My Store"),
            "icon": "fas fa-store-alt",
            "url_name": "dash:store_settings",
        })
        menu.append({
            "title": _("Available Products"),
            "icon": "fas fa-store",
            "url_name": "dash:affiliate_catalog",
        })
        menu.append({
            "title": _("My Catalog"),
            "icon": "fas fa-boxes",
            "url_name": "dash:my_catalog",
        })

    if is_affiliate:
        menu.append({
            "title": _("Semi-Affiliates"),
            "icon": "fas fa-user-friends",
            "url_name": "dash:semi_affiliate_list",
        })

    return menu


def dashboard_sidebar(request):
    """
    Returns the dashboard menu items with RBAC flags (cached by role).
    """
    is_auth = request.user.is_authenticated
    is_super = request.user.is_superuser
    profile = getattr(request.user, "profile", None) if hasattr(request.user, "profile") else None
    role = getattr(profile, "role", None)
    is_trusted = getattr(profile, "is_trusted", False) if profile else False
    return {
        "dashboard_menu": _build_menu(is_auth, is_super, role, is_trusted),
    }
