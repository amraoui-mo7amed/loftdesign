import json

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import models
from django.urls import reverse
from decimal import Decimal

from ..decorator import role_required
from ..utils import notify_user, build_order_chain_breakdown
from user_auth.models import UserProfile, Wallet, Transaction
from ..models import Order

ADMIN = UserProfile.roleChoices.ADMIN
AFFILIATE = UserProfile.roleChoices.AFFILIATE
SEMI = UserProfile.roleChoices.SEMI_AFFILIATE
PROVIDER = UserProfile.roleChoices.PROVIDER

BUSINESS_ROLES = [ADMIN, AFFILIATE, SEMI, PROVIDER]


@role_required(allowed_roles=BUSINESS_ROLES)
def wallet_list(request):
    """Unified wallet list — admin sees all, affiliate sees own + semi, semi/provider see own."""
    profile = request.user.profile
    role = profile.role
    is_admin = role == ADMIN or request.user.is_superuser

    # Semi-affiliates go directly to their own wallet
    if role == SEMI:
        return redirect("dash:wallet_detail")

    if is_admin:
        wallets = Wallet.objects.select_related("user__profile").exclude(user=request.user)
    elif role == AFFILIATE:
        semi_ids = UserProfile.objects.filter(
            parent_affiliate=profile, role=SEMI
        ).values_list("user_id", flat=True)
        wallets = Wallet.objects.filter(
            user_id__in=semi_ids
        ).select_related("user__profile")
    else:
        wallets = Wallet.objects.none()

    q = request.GET.get("q", "").strip()
    if q:
        wallets = wallets.filter(
            models.Q(user__username__icontains=q) | models.Q(user__email__icontains=q)
        )

    role_filter = request.GET.get("role", "").strip()
    selected_role_label = None
    if is_admin and role_filter:
        wallets = wallets.filter(user__profile__role=role_filter)
        role_labels = dict(UserProfile.roleChoices.choices)
        selected_role_label = role_labels.get(role_filter)

    order = request.GET.get("order", "-balance")
    if order.lstrip("-") in ("balance", "pending_balance", "user__username"):
        wallets = wallets.order_by(order)

    paginator = Paginator(wallets, 20)
    page = request.GET.get("page")
    page_obj = paginator.get_page(page)

    role_choices = [
        {"value": "admin", "label": _("Admin")},
        {"value": "affiliate", "label": _("Affiliate")},
        {"value": "semi_affiliate", "label": _("Semi-Affiliate")},
        {"value": "provider", "label": _("Provider")},
    ]

    return render(request, "wallets/wallet_list.html", {
        "page_obj": page_obj,
        "q": q,
        "role_filter": role_filter,
        "role_choices": role_choices if is_admin else [],
        "selected_role_label": selected_role_label,
        "is_admin": is_admin,
        "title": _("Wallets"),
    })


@role_required(allowed_roles=BUSINESS_ROLES)
def wallet_detail(request, user_id=None):
    """Display a user's wallet with transaction history.
    Admin can view any. Affiliate can view own + semi. Semi/provider can view own only."""
    profile = request.user.profile
    role = profile.role

    if user_id is None or user_id == request.user.id:
        target_user = request.user
    elif role == ADMIN:
        target_user = get_object_or_404(User, pk=user_id)
    elif role == AFFILIATE:
        semi = get_object_or_404(UserProfile, user_id=user_id, role=SEMI, parent_affiliate=profile)
        target_user = semi.user
    else:
        return redirect("dash:wallet_list")

    wallet, _wcreated = Wallet.objects.get_or_create(user=target_user)
    transactions = Transaction.objects.filter(wallet=wallet).select_related(
        "order", "source_user", "source_product"
    )

    q = request.GET.get("q", "").strip()
    if q:
        transactions = transactions.filter(
            models.Q(description__icontains=q)
            | models.Q(source_user__username__icontains=q)
            | models.Q(source_user__first_name__icontains=q)
            | models.Q(source_user__last_name__icontains=q)
            | models.Q(source_product__title__icontains=q)
        )

    type_filter = request.GET.get("type", "").strip()
    if type_filter:
        transactions = transactions.filter(transaction_type=type_filter)

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        transactions = transactions.filter(status=status_filter)

    total_earned = Transaction.objects.filter(
        wallet=wallet,
        transaction_type=Transaction.TransactionType.EARNING,
        status=Transaction.TransactionStatus.COMPLETED,
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    total_withdrawn = Transaction.objects.filter(
        wallet=wallet,
        transaction_type=Transaction.TransactionType.WITHDRAWAL,
        status=Transaction.TransactionStatus.COMPLETED,
    ).aggregate(total=models.Sum("amount"))["total"] or 0

    paginator = Paginator(transactions, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Build chain breakdown for admin on transactions with orders
    for tx in page_obj.object_list:
        tx.chain_details_json = "null"
        if tx.order and role == ADMIN:
            try:
                breakdown = build_order_chain_breakdown(tx.order)
                tx.chain_details_json = json.dumps(breakdown)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.exception("Chain breakdown failed for order %s: %s", tx.order.id, e)
                tx.chain_details_json = "null"

    is_own = target_user == request.user

    type_choices = [
        {"value": "", "label": _("All Types")},
        {"value": "earning", "label": _("Earning")},
        {"value": "withdrawal", "label": _("Withdrawal")},
        {"value": "adjustment", "label": _("Adjustment")},
    ]
    status_choices = [
        {"value": "", "label": _("All Statuses")},
        {"value": "completed", "label": _("Completed")},
        {"value": "pending", "label": _("Pending")},
        {"value": "failed", "label": _("Failed")},
    ]

    return render(request, "wallets/wallet.html", {
        "wallet": wallet,
        "page_obj": page_obj,
        "total_earned": total_earned,
        "total_withdrawn": total_withdrawn,
        "q": q,
        "type_filter": type_filter,
        "type_choices": type_choices,
        "status_filter": status_filter,
        "status_choices": status_choices,
        "target_user": target_user,
        "is_own": is_own,
        "is_admin": role == ADMIN,
        "title": _("Wallet"),
    })


@role_required(allowed_roles=[ADMIN])
def withdrawal_request_list(request):
    """Admin: list of users who have made withdrawal requests."""
    users_with_withdrawals = User.objects.filter(
        wallet__transactions__transaction_type=Transaction.TransactionType.WITHDRAWAL
    ).annotate(
        last_withdrawal=models.Max("wallet__transactions__created_at"),
        total_withdrawn=models.Sum(
            "wallet__transactions__amount",
            filter=models.Q(wallet__transactions__transaction_type=Transaction.TransactionType.WITHDRAWAL)
        ),
        pending_count=models.Count(
            "wallet__transactions",
            filter=models.Q(
                wallet__transactions__transaction_type=Transaction.TransactionType.WITHDRAWAL,
                wallet__transactions__status=Transaction.TransactionStatus.PENDING,
            )
        ),
    ).distinct().order_by("-last_withdrawal")

    q = request.GET.get("q", "").strip()
    if q:
        users_with_withdrawals = users_with_withdrawals.filter(
            models.Q(username__icontains=q)
            | models.Q(first_name__icontains=q)
            | models.Q(last_name__icontains=q)
            | models.Q(email__icontains=q)
        )

    role_filter = request.GET.get("role", "").strip()
    if role_filter:
        users_with_withdrawals = users_with_withdrawals.filter(
            profile__role=role_filter
        )

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        users_with_withdrawals = users_with_withdrawals.filter(
            wallet__transactions__created_at__gte=date_from
        )
    if date_to:
        users_with_withdrawals = users_with_withdrawals.filter(
            wallet__transactions__created_at__lte=date_to + " 23:59:59"
        )

    paginator = Paginator(users_with_withdrawals, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    role_choices = [
        {"value": "admin", "label": _("Admin")},
        {"value": "affiliate", "label": _("Affiliate")},
        {"value": "semi_affiliate", "label": _("Semi-Affiliate")},
        {"value": "provider", "label": _("Provider")},
    ]

    return render(request, "wallets/withdrawal_list.html", {
        "page_obj": page_obj,
        "q": q,
        "role_filter": role_filter,
        "role_choices": role_choices,
        "date_from": date_from,
        "date_to": date_to,
        "title": _("Withdrawal Requests"),
        "is_user_list": True,
    })


@role_required(allowed_roles=[ADMIN])
def user_withdrawals(request, user_id):
    """Admin: view a specific user's withdrawal history."""
    target_user = get_object_or_404(User, pk=user_id)
    withdrawals = Transaction.objects.filter(
        wallet__user=target_user,
        transaction_type=Transaction.TransactionType.WITHDRAWAL,
    ).select_related("wallet__user").order_by("-created_at")

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        withdrawals = withdrawals.filter(status=status_filter)

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        withdrawals = withdrawals.filter(created_at__gte=date_from)
    if date_to:
        withdrawals = withdrawals.filter(created_at__lte=date_to + " 23:59:59")

    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "wallets/withdrawal_list.html", {
        "page_obj": page_obj,
        "target_user": target_user,
        "status_filter": status_filter,
        "status_choices": [
            {"value": "", "label": _("All Statuses")},
            {"value": "pending", "label": _("Pending")},
            {"value": "completed", "label": _("Approved")},
            {"value": "failed", "label": _("Rejected")},
        ],
        "date_from": date_from,
        "date_to": date_to,
        "title": _("Withdrawals — %(name)s") % {"name": target_user.get_full_name() or target_user.username},
    })


@role_required(allowed_roles=[ADMIN])
def handle_withdrawal(request, pk):
    """Admin: approve or reject a withdrawal request"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    withdrawal = get_object_or_404(Transaction, pk=pk, transaction_type=Transaction.TransactionType.WITHDRAWAL)
    action = request.POST.get("action")
    wallet = withdrawal.wallet

    if action == "approve":
        withdrawal.status = Transaction.TransactionStatus.COMPLETED
        wallet.balance -= withdrawal.amount
        wallet.save(update_fields=["balance"])
        withdrawal.save(update_fields=["status"])
        notify_user(
            wallet.user,
            _("Withdrawal Approved"),
            _('Your withdrawal of %(amount)s DZD has been approved.')
            % {"amount": f"{withdrawal.amount:,.2f}"},
            notification_type="success",
            link=reverse("dash:wallet_detail"),
        )
        return JsonResponse({"success": True, "message": _("Withdrawal approved.")})
    elif action == "reject":
        withdrawal.status = Transaction.TransactionStatus.FAILED
        withdrawal.save(update_fields=["status"])
        notify_user(
            wallet.user,
            _("Withdrawal Rejected"),
            _('Your withdrawal of %(amount)s DZD has been rejected.')
            % {"amount": f"{withdrawal.amount:,.2f}"},
            notification_type="error",
            link=reverse("dash:wallet_detail"),
        )
        return JsonResponse({"success": True, "message": _("Withdrawal rejected.")})

    return JsonResponse({"success": False}, status=400)


@role_required(allowed_roles=BUSINESS_ROLES)
def request_withdrawal(request):
    """User requests a withdrawal from their wallet.
    Admin withdrawals are immediate (COMPLETED). Others require admin approval (PENDING)."""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    try:
        amount = Decimal(str(request.POST.get("amount", 0)))
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return JsonResponse({"success": False, "errors": {"amount": [_("Invalid amount.")]}})

    if amount <= 0:
        return JsonResponse({"success": False, "errors": {"amount": [_("Amount must be positive.")]}})

    wallet, _wcreated = Wallet.objects.get_or_create(user=request.user)
    if amount > wallet.balance:
        return JsonResponse({"success": False, "errors": {"amount": [_("Insufficient balance.")]}})

    is_admin = request.user.profile.role == ADMIN

    if is_admin:
        wallet.balance -= amount
        wallet.save(update_fields=["balance"])
        Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            amount=amount,
            description=_("Admin withdrawal — %(amount)s DZD") % {"amount": amount},
            status=Transaction.TransactionStatus.COMPLETED,
        )
        return JsonResponse({
            "success": True,
            "message": _("Withdrawal completed."),
        })
    else:
        Transaction.objects.create(
            wallet=wallet,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            amount=amount,
            description=_("Withdrawal request for %(amount)s DZD") % {"amount": amount},
            status=Transaction.TransactionStatus.PENDING,
        )

        for admin in User.objects.filter(is_superuser=True):
            notify_user(
                admin,
                _("Withdrawal Request"),
                _('%(user)s requested a withdrawal of %(amount)s DZD.')
                % {"user": request.user.get_full_name() or request.user.username, "amount": amount},
                notification_type="warning",
                link=reverse("dash:withdrawal_request_list"),
            )

        return JsonResponse({
            "success": True,
            "message": _("Withdrawal request submitted. Awaiting admin approval."),
        })


@role_required(allowed_roles=[ADMIN])
def clear_wallet(request, user_id):
    """Admin: clear all transactions and reset a user's wallet balance to 0"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    wallet = get_object_or_404(Wallet, user_id=user_id)
    wallet.balance = Decimal("0.00")
    wallet.pending_balance = Decimal("0.00")
    wallet.save(update_fields=["balance", "pending_balance"])

    wallet.transactions.all().delete()

    return JsonResponse({
        "success": True,
        "message": _("Wallet cleared."),
    })
