from django.utils.translation import gettext_lazy as _


def dashboard_sidebar(request):
    """
    Returns the dashboard menu items with RBAC flags.
    """
    return {
        "dashboard_menu": [
            {
                "title": _("Dashboard"),
                "icon": "fas fa-th-large",
                "url_name": "dash:dash_home",
                "admin_only": False,
            },
            {
                "title": _("users"),
                "icon": "fas fa-users",
                "url_name": "dash:user_list",
                "admin_only": True,
            }
        ],
    }
