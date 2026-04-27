from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from user_auth.models import UserProfile
from django.db.models import Q
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from dashboard.utils import send_account_activation_email
from dashboard.decorator import admin_required
from django.db import transaction


@admin_required
def user_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")

    profiles_list = (
        UserProfile.objects.select_related("user").all().order_by("-created_at")
    )

    if query:
        profiles_list = profiles_list.filter(
            Q(user__email__icontains=query)
            | Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        )

    if status:
        is_approved = status == "approved"
        profiles_list = profiles_list.filter(is_approved=is_approved)

    # Pagination
    paginator = Paginator(profiles_list, 12)  # 12 users per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    status_choices = [
        ("", _("All Status")),
        ("approved", _("Approved")),
        ("pending", _("Pending")),
    ]

    selected_status_label = _("All Status")
    for val, label in status_choices:
        if val == status:
            selected_status_label = label
            break

    context = {
        "page_obj": page_obj,
        "profiles": page_obj,  # Compatibility with template
        "status_choices": status_choices,
        "query": query,
        "selected_status": status,
        "selected_status_label": selected_status_label,
    }

    return render(request, "users/list.html", context)


@admin_required
def user_details(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    return render(request, "users/details.html", {"profile": profile})


@admin_required
def user_delete(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        full_name = profile.user.get_full_name() or profile.user.username
        profile.user.delete()  # Cascade will delete the profile

        return JsonResponse(
            {
                "success": True,
                "message": _("User %(name)s deleted successfully.")
                % {"name": full_name},
                "redirect_url": reverse("dash:user_list"),
            }
        )

    return redirect("dash:user_details", pk=pk)


@admin_required
def user_approve(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                profile.is_approved = True
                profile.save()

                # Send activation email
                email_sent = send_account_activation_email(request, profile)

                if not email_sent:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {
                            "success": False,
                            "message": _(
                                "Failed to send activation email. Approval cancelled."
                            ),
                        }
                    )

                full_name = profile.user.get_full_name() or profile.user.username
                success_msg = _("User %(name)s approved successfully.") % {
                    "name": full_name
                }
                return JsonResponse({"success": True, "message": success_msg})
        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "message": _("An error occurred during approval: %(error)s")
                    % {"error": str(e)},
                }
            )

    return redirect("dash:user_details", pk=pk)
