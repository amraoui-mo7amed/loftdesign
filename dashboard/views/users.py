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
from django.db import transaction
from dashboard.utils import send_account_activation_email, notify_user
from dashboard.decorator import role_required
from dashboard.models import Notification, Product, PartnerPrice, AffiliateStore, StoreVisit, LoftPrice
from user_auth.utils import generate_affiliate_code, user_profile_upload_path
from decimal import Decimal
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
        status=Order.OrderStatus.DELIVERED
    )
    user_product_ids = set(
        Product.objects.filter(user=profile.user).values_list("id", flat=True)
    )
    confirmed_orders = [
        o for o in confirmed_orders
        if any(item.get("product_id") in user_product_ids for item in o.items)
    ]
    
    confirmed_sales_count = len(confirmed_orders)
    total_confirmed_price = Decimal("0")
    for o in confirmed_orders:
        for item in o.items:
            price = Decimal(str(item.get("price", 0) or 0))
            qty = int(item.get("quantity", 1))
            total_confirmed_price += price * qty

    # Debt: Total commission earned by the platform from this provider
    total_debt = (total_confirmed_price * profile.commission) / 100

    # Affiliate store data
    store = None
    store_visits = 0
    store_orders = []
    referred_order_count = 0
    total_earnings = Decimal("0.00")
    unpaid_earnings = Decimal("0.00")
    referred_orders_data = []
    if profile.role in (UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.SEMI_AFFILIATE):
        store, created = AffiliateStore.objects.get_or_create(
            affiliate=profile,
            defaults={"store_name": profile.user.get_full_name() or profile.user.username}
        )
        store_visits = StoreVisit.objects.filter(store=store).count()
        referred_codes = [profile.affiliate_code]
        if profile.role == UserProfile.roleChoices.AFFILIATE:
            semi_codes = UserProfile.objects.filter(
                parent_affiliate=profile, is_approved=True
            ).exclude(affiliate_code__isnull=True).exclude(affiliate_code="").values_list("affiliate_code", flat=True)
            referred_codes.extend(semi_codes)
        referred_orders_qs = Order.objects.filter(referred_by__in=referred_codes)
        referred_order_count = referred_orders_qs.count()
        store_orders = referred_orders_qs.order_by("-created_at")[:10]

        # Batch-load LoftPrices for all DELIVERED orders
        delivered_referred = [o for o in referred_orders_qs if o.status == Order.OrderStatus.DELIVERED]
        all_product_ids = set()
        for o in delivered_referred:
            for item in o.items:
                pid = item.get("product_id")
                if pid:
                    all_product_ids.add(pid)
        loft_prices = {
            lp.product_id: lp
            for lp in LoftPrice.objects.filter(product_id__in=all_product_ids)
        }

        for order in referred_orders_qs:
            earnings = Decimal("0.00")
            if order.status == Order.OrderStatus.DELIVERED:
                for item in order.items:
                    product_id = item.get("product_id")
                    price = Decimal(str(item.get("price", 0))) or Decimal("0")
                    quantity = int(item.get("quantity", 1))
                    if product_id and product_id in loft_prices:
                        margin = price - loft_prices[product_id].loft_default_wholesale_price
                        if margin > 0:
                            earnings += margin * quantity
                total_earnings += earnings
                if not order.commission_paid:
                    unpaid_earnings += earnings
            referred_orders_data.append({
                "order": order,
                "earnings": earnings,
            })

    context = {
        "profile": profile,
        "confirmed_sales_count": confirmed_sales_count,
        "total_confirmed_price": total_confirmed_price,
        "total_debt": total_debt,
        "store": store,
        "store_visits": store_visits,
        "store_orders": store_orders,
        "referred_order_count": referred_order_count,
        "total_earnings": total_earnings,
        "unpaid_earnings": unpaid_earnings,
        "referred_orders_data": referred_orders_data,
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


@role_required(allowed_roles=[UserProfile.roleChoices.PROVIDER, UserProfile.roleChoices.AFFILIATE, UserProfile.roleChoices.SEMI_AFFILIATE, UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.FINAL_CLIENT])
def profile_update(request):
    """AJAX view for providers/affiliates/admins to update their own profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    if created and request.user.is_superuser:
        profile.role = UserProfile.roleChoices.ADMIN
        profile.save()

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


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.AFFILIATE])
def semi_affiliate_create(request):
    """AJAX: an affiliate creates a semi-affiliate (sub-affiliate) under them, sends invitation email"""
    profile = get_object_or_404(UserProfile, user=request.user)
    is_admin = request.user.is_superuser

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone", "")

        errors = {}
        if not first_name: errors["first_name"] = [_("First name is required")]
        if not email: errors["email"] = [_("Email is required")]
        if User.objects.filter(email=email).exists():
            errors["email"] = [_("This email is already registered")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            affiliate_code = generate_affiliate_code()
            username = email.split("@")[0]
            if User.objects.filter(username=username).exists():
                username = f"{username}_{secrets.token_hex(2)}"

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username, email=email,
                    first_name=first_name, last_name=last_name, is_active=True
                )
                user.set_unusable_password()
                user.save()

                UserProfile.objects.create(
                    user=user,
                    role=UserProfile.roleChoices.SEMI_AFFILIATE,
                    parent_affiliate=profile if not is_admin else None,
                    affiliate_code=affiliate_code,
                    phone_number=phone,
                    is_approved=True,
                    approved_at=timezone.now(),
                )

                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                set_password_url = request.build_absolute_uri(
                    reverse('user_auth:set_password', kwargs={'uidb64': uidb64, 'token': token})
                )

                creator_name = request.user.get_full_name() or request.user.username
                email_html = render_to_string('emails/semi_affiliate_set_password.html', {
                    'first_name': first_name,
                    'username': username,
                    'email': email,
                    'creator_name': creator_name,
                    'set_password_url': set_password_url,
                })

                email_msg = EmailMessage(
                    subject="LOFT Design - Your Semi-Affiliate Account / Votre compte sous-affilié",
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
                    transaction.set_rollback(True)
                    return JsonResponse({
                        "success": False,
                        "errors": {
                            "email": [_("Account could not be created because the invitation email failed to send. Please check your SMTP settings.")]
                        }
                    })

            return JsonResponse({
                "success": True,
                "message": _("Semi-affiliate '%(name)s' created. Invitation sent to %(email)s.")
                % {"name": f"{first_name} {last_name}", "email": email},
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.AFFILIATE])
@role_required(allowed_roles=[UserProfile.roleChoices.ADMIN, UserProfile.roleChoices.AFFILIATE])
def semi_affiliate_delete(request, pk):
    """AJAX: delete a semi-affiliate account"""
    if request.method == "POST":
        profile = get_object_or_404(UserProfile, pk=pk, role=UserProfile.roleChoices.SEMI_AFFILIATE)
        full_name = profile.user.get_full_name() or profile.user.username
        profile.user.delete()
        return JsonResponse({
            "success": True,
            "message": _("Semi-affiliate %(name)s deleted successfully.") % {"name": full_name},
        })
    return JsonResponse({"success": False}, status=400)


def semi_affiliate_list(request):
    """List semi-affiliates under the current affiliate"""
    q = request.GET.get("q", "")
    parent_filter = request.GET.get("parent", "")
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.user.is_superuser:
        qs = UserProfile.objects.filter(
            role=UserProfile.roleChoices.SEMI_AFFILIATE
        ).select_related("user", "parent_affiliate__user")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
                | Q(affiliate_code__icontains=q)
            )
        if parent_filter:
            qs = qs.filter(parent_affiliate_id=parent_filter)
        semi_affiliates = qs
        affiliate_options = [
            {"value": a.id, "label": f"{a.user.get_full_name() or a.user.username} ({a.affiliate_code})"}
            for a in UserProfile.objects.filter(
                role=UserProfile.roleChoices.AFFILIATE, is_approved=True
            ).select_related("user")
        ]
    else:
        qs = UserProfile.objects.filter(
            parent_affiliate=profile, role=UserProfile.roleChoices.SEMI_AFFILIATE
        ).select_related("user")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
                | Q(affiliate_code__icontains=q)
            )
        semi_affiliates = qs
        affiliate_options = []

    return render(request, "users/semi_affiliate_list.html", {
        "semi_affiliates": semi_affiliates,
        "affiliate_options": affiliate_options,
        "selected_parent": parent_filter,
        "query": q,
    })


from user_auth.utils import generate_affiliate_code


_RC = UserProfile.roleChoices


@role_required(allowed_roles=[_RC.ADMIN, _RC.AFFILIATE, _RC.SEMI_AFFILIATE])
def end_client_list(request):
    """List end clients — semi sees own, affiliate sees chain, admin sees all"""
    profile = get_object_or_404(UserProfile, user=request.user)
    q = request.GET.get("q", "")

    if request.user.is_superuser:
        qs = UserProfile.objects.filter(
            role=_RC.FINAL_CLIENT
        ).select_related("user", "created_by__user")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
            )
    elif profile.role == _RC.AFFILIATE:
        semi_ids = UserProfile.objects.filter(
            parent_affiliate=profile, role=_RC.SEMI_AFFILIATE
        ).values_list("id", flat=True)
        qs = UserProfile.objects.filter(
            role=_RC.FINAL_CLIENT
        ).filter(
            Q(created_by_id__in=list(semi_ids)) | Q(created_by=profile)
        ).select_related("user", "created_by__user")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
            )
    else:
        qs = UserProfile.objects.filter(
            role=_RC.FINAL_CLIENT, created_by=profile
        ).select_related("user")
        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
            )

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    is_semi = profile.role == _RC.SEMI_AFFILIATE
    return render(request, "users/end_client_list.html", {
        "page_obj": page_obj,
        "query": q,
        "is_semi": is_semi,
        "title": _("End Clients"),
    })


@role_required(allowed_roles=[_RC.ADMIN, _RC.AFFILIATE, _RC.SEMI_AFFILIATE])
def end_client_create(request):
    """AJAX: admin/affiliate/semi-affiliate creates an end client and sends invitation email"""
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone", "")

        errors = {}
        if not first_name:
            errors["first_name"] = [_("First name is required")]
        if not email:
            errors["email"] = [_("Email is required")]
        if User.objects.filter(email=email).exists():
            errors["email"] = [_("This email is already registered")]

        if errors:
            return JsonResponse({"success": False, "errors": errors})

        try:
            username = email.split("@")[0]
            if User.objects.filter(username=username).exists():
                username = f"{username}_{secrets.token_hex(2)}"

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username, email=email,
                    first_name=first_name, last_name=last_name, is_active=True
                )
                user.set_unusable_password()
                user.save()

                UserProfile.objects.create(
                    user=user,
                    role=_RC.FINAL_CLIENT,
                    created_by=profile,
                    phone_number=phone,
                    is_approved=True,
                )

                token_generator = PasswordResetTokenGenerator()
                token = token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                set_password_url = request.build_absolute_uri(
                    reverse('user_auth:set_password', kwargs={'uidb64': uidb64, 'token': token})
                )

                creator_name = request.user.get_full_name() or request.user.username
                email_html = render_to_string('emails/end_client_set_password.html', {
                    'first_name': first_name,
                    'username': username,
                    'email': email,
                    'creator_name': creator_name,
                    'set_password_url': set_password_url,
                })

                email_msg = EmailMessage(
                    subject="LOFT Design - Your Client Account / حساب العميل الخاص بك",
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
                    transaction.set_rollback(True)
                    return JsonResponse({
                        "success": False,
                        "errors": {
                            "email": [_("Account could not be created because the invitation email failed to send.")]
                        }
                    })

            return JsonResponse({
                "success": True,
                "message": _("End client '%(name)s' created. Invitation sent to %(email)s.")
                % {"name": f"{first_name} {last_name}", "email": email},
            })
        except Exception as e:
            return JsonResponse({"success": False, "errors": {"system": [str(e)]}})

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=[_RC.ADMIN, _RC.AFFILIATE, _RC.SEMI_AFFILIATE])
def end_client_delete(request, pk):
    """AJAX: delete an end client account"""
    if request.method == "POST":
        profile = get_object_or_404(UserProfile, pk=pk, role=_RC.FINAL_CLIENT)
        if not request.user.is_superuser and profile.created_by.user != request.user:
            return JsonResponse({"success": False, "message": _("Permission denied.")}, status=403)
        full_name = profile.user.get_full_name() or profile.user.username
        profile.user.delete()
        return JsonResponse({
            "success": True,
            "message": _("End client %(name)s deleted successfully.") % {"name": full_name},
        })
    return JsonResponse({"success": False}, status=400)
