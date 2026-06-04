from django.utils.translation import gettext_lazy as _
from functools import lru_cache


def get_dashboard_menu(user):
    """
    Returns the static list of dashboard menu items based on user role.
    """
    menu = [
        {
            "title": _("Dashboard"),
            "icon": "fas fa-th-large",
            "url_name": "dash:dash_home",
        },
    ]

    if not user.is_authenticated:
        return menu

    is_admin = user.is_superuser
    role = getattr(user.profile, "role", None) if hasattr(user, "profile") else None

    # Admin only links
    if is_admin:
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

    # Both Admin and Provider links
    if is_admin or role == "provider":
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

    return menu


def dashboard_sidebar(request):
    """
    Returns the dashboard menu items with RBAC flags.
    """
    return {
        "dashboard_menu": get_dashboard_menu(request.user),
    }
