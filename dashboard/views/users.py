from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from user_auth.models import UserProfile
from django.db.models import Q
from django.utils.translation import gettext as _
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from dashboard.utils import send_account_activation_email, notify_user
from dashboard.decorator import role_required
from dashboard.models import Notification, Product
from django.db import transaction
import secrets

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def provider_create(request):
    """AJAX view to create a new provider and send welcome email"""
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        commission = request.POST.get("commission")
        is_trusted = request.POST.get("is_trusted") == "on"

        errors = {}
        if not first_name: errors["first_name"] = [_("First name is required")]
        if not email: errors["email"] = [_("Email is required")]
        if not commission: errors["commission"] = [_("Commission is required")]
        if User.objects.filter(email=email).exists():
            errors["email"] = [_("This email is already in use")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            with transaction.atomic():
                # Generate unique username
                username = email.split('@')[0]
                if User.objects.filter(username=username).exists():
                    username = f"{username}_{secrets.token_hex(2)}"

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
                user.set_unusable_password()
                user.save()

                # Create Profile
                profile = UserProfile.objects.create(
                    user=user,
                    phone_number=phone,
                    address=address,
                    commission=commission,
                    is_approved=True,
                    is_trusted=is_trusted,
                    role=UserProfile.roleChoices.PROVIDER
                )

                # Generate password-set token
                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                set_password_url = request.build_absolute_uri(
                    reverse('user_auth:set_password', kwargs={'uidb64': uidb64, 'token': token})
                )

                # Prepare Email
                email_html = render_to_string('emails/provider_set_password.html', {
                    'first_name': first_name,
                    'username': username,
                    'email': email,
                    'set_password_url': set_password_url,
                })

                email_msg = EmailMessage(
                    subject="LOFT Design - Set Your Password / Définissez votre mot de passe",
                    body=email_html,
                    from_email=settings.EMAIL_HOST_USER,
                    to=[email],
                )
                email_msg.content_subtype = "html"

                try:
                    email_sent = email_msg.send(fail_silently=False)
                    if not email_sent:
                        raise Exception(_("Failed to send email. Account creation rolled back."))
                except Exception as mail_err:
                    # Rolling back transaction because email is mandatory
                    transaction.set_rollback(True)
                    print(f"Critical Mail error: {mail_err}")
                    return JsonResponse({
                        "success": False, 
                        "errors": {
                            "email": [_("Account could not be created because the invitation email failed to send. Please check your SMTP settings.")]
                        }
                    })

                return JsonResponse({
                    "success": True,
                    "message": _("Provider account created and invitation sent successfully."),
                    "redirect_url": reverse("dash:user_list")
                })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def user_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")

    profiles_list = (
        UserProfile.objects.select_related("user")
        .filter(role=UserProfile.roleChoices.PROVIDER)
        .order_by("-created_at")
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


from dashboard.models import Order
from django.db.models import Sum, Count

@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def user_details(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    
    # Financial Analytics for Provider
    confirmed_orders = Order.objects.filter(
        status=Order.OrderStatus.COMPLETED
    )
    user_product_ids = set(
        Product.objects.filter(user=profile.user).values_list("id", flat=True)
    )
    confirmed_orders = [
        o for o in confirmed_orders
        if any(item.get("product_id") in user_product_ids for item in o.items)
    ]
    
    confirmed_sales_count = len(confirmed_orders)
    total_confirmed_price = sum(
        sum(
            (float(item.get("price", 0)) or 0) * int(item.get("quantity", 1))
            for item in o.items
        )
        for o in confirmed_orders
    )

    # Debt: Total commission earned by the platform from this provider
    total_debt = (total_confirmed_price * profile.commission) / 100

    context = {
        "profile": profile,
        "confirmed_sales_count": confirmed_sales_count,
        "total_confirmed_price": total_confirmed_price,
        "total_debt": total_debt,
    }
    return render(request, "users/details.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def user_delete(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        full_name = profile.user.get_full_name() or profile.user.username
        profile.user.delete()  # Cascade will delete the profile

        redirect_url = reverse("dash:affiliate_list") if profile.role == "affiliate" else reverse("dash:user_list")
        return JsonResponse(
            {
                "success": True,
                "message": _("User %(name)s deleted successfully.")
                % {"name": full_name},
                "redirect_url": redirect_url,
            }
        )

    return redirect("dash:user_details", pk=pk)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
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


@role_required(allowed_roles=[UserProfile.roleChoices.PROVIDER, UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.ADMIN])
def profile_update(request):
    """AJAX view for providers/affiliates/admins to update their own profile"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        bio = request.POST.get("bio", "").strip()

        errors = {}
        if not first_name:
            errors["first_name"] = [_("First name is required")]
        if not last_name:
            errors["last_name"] = [_("Last name is required")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            user = profile.user
            user.first_name = first_name
            user.last_name = last_name
            user.save()

            profile.phone_number = phone
            profile.address = address
            profile.bio = bio

            if request.FILES.get("profile_picture"):
                profile.profile_picture = request.FILES["profile_picture"]

            profile.save()

            return JsonResponse({
                "success": True,
                "message": _("Profile updated successfully."),
                "redirect_url": reverse("dash:profile_update"),
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "errors": {"system": [str(e)]},
            })

    context = {
        "profile": profile,
    }
    return render(request, "users/profile_edit.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def user_toggle_block(request, pk):
    """AJAX view to block/unblock a user account"""
    if request.method == "POST":
        profile = get_object_or_404(UserProfile, pk=pk)
        profile.is_blocked = not profile.is_blocked
        profile.save()

        status = _("blocked") if profile.is_blocked else _("unblocked")
        full_name = profile.user.get_full_name() or profile.user.username

        # Send email notification to user
        if profile.is_blocked:
            email_html = render_to_string("emails/account_blocked.html", {
                "full_name": full_name,
            })
            email_msg = EmailMultiAlternatives(
                subject=_("LOFT Design - Account Blocked"),
                body=email_html,
                from_email=settings.EMAIL_HOST_USER,
                to=[profile.user.email],
            )
            email_msg.content_subtype = "html"
            try:
                email_msg.send(fail_silently=True)
            except Exception:
                pass

        return JsonResponse({
            "success": True,
            "message": _("User %(name)s has been %(status)s.") % {"name": full_name, "status": status},
        })

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def affiliate_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")

    profiles_list = (
        UserProfile.objects.select_related("user")
        .filter(role=UserProfile.roleChoices.AFFILIATE)
        .order_by("-created_at")
    )

    if query:
        profiles_list = profiles_list.filter(
            Q(user__email__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
        )

    if status == "approved":
        profiles_list = profiles_list.filter(is_approved=True)
    elif status == "pending":
        profiles_list = profiles_list.filter(is_approved=False)

    paginator = Paginator(profiles_list, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    status_choices = [
        ("", _("All")),
        ("approved", _("Approved")),
        ("pending", _("Pending")),
    ]

    context = {
        "page_obj": page_obj,
        "profiles": page_obj,
        "status_choices": status_choices,
        "query": query,
        "selected_status": status,
        "title": _("Affiliates"),
    }
    return render(request, "users/affiliate_list.html", context)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN])
def affiliate_approve(request, pk):
    if request.method == "POST":
        profile = get_object_or_404(UserProfile, pk=pk, role=UserProfile.roleChoices.AFFILIATE)
        approved = request.POST.get("approved") == "true"

        try:
            with transaction.atomic():
                profile.is_approved = approved
                profile.user.is_active = approved
                if approved:
                    profile.approved_at = timezone.now()
                else:
                    profile.approved_at = None
                profile.save()
                profile.user.save()

                if approved:
                    email_sent = send_affiliate_activation_email(request, profile)
                    if not email_sent:
                        transaction.set_rollback(True)
                        return JsonResponse({
                            "success": False,
                            "message": _("Failed to send activation email. Operation cancelled."),
                        })

                    full_name = profile.user.get_full_name() or profile.user.username
                    return JsonResponse({
                        "success": True,
                        "message": _("%(name)s approved successfully. Activation email sent.") % {"name": full_name},
                    })
                else:
                    full_name = profile.user.get_full_name() or profile.user.username
                    return JsonResponse({
                        "success": True,
                        "message": _("%(name)s has been disapproved.") % {"name": full_name},
                    })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": _("An error occurred: %(error)s") % {"error": str(e)},
            })

    return JsonResponse({"success": False}, status=400)


def send_affiliate_activation_email(request, profile):
    site_name = _("LOFT Design")
    subject = _("Welcome to %(site)s — Your Affiliate Account is Active!") % {"site": site_name}
    login_url = request.build_absolute_uri(reverse("user_auth:login"))

    context = {
        "profile": profile,
        "login_url": login_url,
        "site_name": site_name,
    }

    html_content = render_to_string("email/affiliate_activation.html", context)

    email = EmailMultiAlternatives(
        subject, "", settings.DEFAULT_FROM_EMAIL, [profile.user.email]
    )
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
        return True
    except Exception as e:
        print(f"Failed to send affiliate activation email: {e}")
        return False
