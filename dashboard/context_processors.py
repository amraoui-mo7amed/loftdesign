from django.utils.translation import gettext_lazy as _
from functools import lru_cache


@lru_cache(maxsize=1)
def get_dashboard_menu():
    """
    Returns the static list of dashboard menu items.
    Cached for performance.
    """
    return [
        {
            "title": _("Dashboard"),
            "icon": "fas fa-th-large",
            "url_name": "dash:dash_home",
            "admin_only": False,
        },
        {
            "title": _("Users"),
            "icon": "fas fa-users",
            "url_name": "dash:user_list",
            "admin_only": True,
        },
        {
            "title": _("Portfolio"),
            "icon": "fas fa-briefcase",
            "url_name": "dash:portfolio_list",
            "admin_only": True,
        },
        {
            "title": _("Products"),
            "icon": "fas fa-box-open",
            "url_name": "dash:product_list",
            "admin_only": True,
        },
        {
            "title": _("Orders"),
            "icon": "fas fa-shopping-cart",
            "url_name": "dash:order_list",
            "admin_only": True,
        },
    ]


def dashboard_sidebar(request):
    """
    Returns the dashboard menu items with RBAC flags.
    """
    return {
        "dashboard_menu": get_dashboard_menu(),
    }
