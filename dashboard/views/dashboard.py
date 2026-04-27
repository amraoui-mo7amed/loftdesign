from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
from user_auth.models import UserProfile
from django.contrib.auth.models import User
import json


@login_required
def dash_home(request):
    user_profile = getattr(request.user, "profile", None)

    # Common Data
    context = {
        "role": "admin" if request.user.is_superuser else "user",
        "notifications": [
            {
                "type": "warning",
                "title": _("System Alert"),
                "message": _("New security update available."),
                "time": "2h ago",
            },
            {
                "type": "info",
                "title": _("Welcome"),
                "message": _("Welcome to your new dashboard!"),
                "time": "5h ago",
            },
        ],
    }

    if request.user.is_superuser:
        # Platform Admin Statistics
        total_users = User.objects.count()
        approved_users = UserProfile.objects.filter(is_approved=True).count()
        pending_approval = UserProfile.objects.filter(is_approved=False).count()
        staff_count = User.objects.filter(is_staff=True).count()

        context.update(
            {
                "stat_1": {
                    "title": _("Total Users"),
                    "value": total_users,
                    "icon": "fa-users",
                    "color": "primary",
                },
                "stat_2": {
                    "title": _("Approved Users"),
                    "value": approved_users,
                    "icon": "fa-user-check",
                    "color": "success",
                },
                "stat_3": {
                    "title": _("Pending Approval"),
                    "value": pending_approval,
                    "icon": "fa-user-clock",
                    "color": "warning",
                },
                "stat_4": {
                    "title": _("Staff Members"),
                    "value": staff_count,
                    "icon": "fa-user-shield",
                    "color": "info",
                },
                "chart_title": _("Registration Trends"),
                "user_dist_labels": json.dumps(
                    [str(_("Jan")), str(_("Feb")), str(_("Mar"))]
                ),
                "user_dist_values": json.dumps(
                    [total_users, approved_users, pending_approval]
                ),
                "list_title": _("Recent Registrations"),
                "recent_users": UserProfile.objects.select_related("user").order_by(
                    "-created_at"
                )[:5],
            }
        )
    else:
        # Generic User Dashboard with dummy data
        context.update(
            {
                "stat_1": {
                    "title": _("Active Projects"),
                    "value": "12",
                    "trend": "2.4",
                    "icon": "fa-rocket",
                    "color": "primary",
                },
                "stat_2": {
                    "title": _("Completed Tasks"),
                    "value": "85",
                    "trend": "1.1",
                    "icon": "fa-check-double",
                    "color": "success",
                },
                "stat_3": {
                    "title": _("Pending Actions"),
                    "value": "4",
                    "trend": "0.5",
                    "icon": "fa-clock",
                    "color": "warning",
                },
                "stat_4": {
                    "title": _("Total Hours"),
                    "value": "320",
                    "icon": "fa-stopwatch",
                    "color": "info",
                },
                "chart_title": _("Weekly Activity"),
                "chart_values": json.dumps([12, 15, 8, 19, 22, 18, 25]),
                "list_title": _("Upcoming Tasks"),
                "list_items": [
                    _("Launch Website"),
                    _("Database Migration"),
                    _("Client Meeting"),
                ],
            }
        )

    return render(request, "dash/dash_home.html", context)

    return render(request, "dash/dash_home.html", context)
