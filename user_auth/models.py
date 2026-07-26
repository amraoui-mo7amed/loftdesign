from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .utils import user_profile_upload_path


class UserProfile(models.Model):
    class roleChoices(models.TextChoices):
        ADMIN = "admin", _("Admin")
        PROVIDER = "provider", _("Provider")
        AFFILIATE = "affiliate", _("Affiliate")
        SEMI_AFFILIATE = "semi_affiliate", _("Semi-Affiliate")
        PROFESSIONAL_CLIENT = "professional_client", _("Professional Client")
        FINAL_CLIENT = "final_client", _("Final Client")

    role = models.CharField(
        _("Role"), max_length=20, choices=roleChoices.choices, default=roleChoices.PROVIDER
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Generic Profile Fields
    profile_picture = models.ImageField(
        _("Profile Picture"), upload_to=user_profile_upload_path, blank=True, null=True
    )
    bio = models.TextField(_("Bio"), max_length=500, blank=True)
    birth_date = models.DateField(_("Birth Date"), null=True, blank=True)

    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    commission = models.DecimalField(
        _("Commission (%)"),
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Commission percentage for the provider"),
    )

    # Affiliate Specific
    affiliate_code = models.CharField(
        _("Affiliate Code"), max_length=20, unique=True, blank=True, null=True
    )
    parent_affiliate = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="semi_affiliates", verbose_name=_("Parent Affiliate"),
        help_text=_("The affiliate who created this semi-affiliate account")
    )
    created_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="end_clients", verbose_name=_("Created By"),
        help_text=_("The semi-affiliate who created this end client account")
    )
    approved_at = models.DateTimeField(_("Approved At"), null=True, blank=True)

    # System Fields
    is_approved = models.BooleanField(_("Is Approved"), default=False)
    is_trusted = models.BooleanField(_("Is Trusted"), default=False)
    is_blocked = models.BooleanField(_("Is Blocked"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")


class Wallet(models.Model):
    """Wallet for each business account — tracks earnings and pending balance"""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="wallet",
        verbose_name=_("User")
    )
    balance = models.DecimalField(
        _("Balance (DZD)"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Available balance that can be withdrawn")
    )
    pending_balance = models.DecimalField(
        _("Pending Balance (DZD)"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Earnings from orders not yet delivered")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.balance} DZD"


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        EARNING = "earning", _("Earning")
        WITHDRAWAL = "withdrawal", _("Withdrawal")
        ADJUSTMENT = "adjustment", _("Adjustment")

    class TransactionStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    wallet = models.ForeignKey(
        Wallet, on_delete=models.CASCADE, related_name="transactions",
        verbose_name=_("Wallet")
    )
    transaction_type = models.CharField(
        _("Type"), max_length=20, choices=TransactionType.choices,
        default=TransactionType.EARNING
    )
    amount = models.DecimalField(
        _("Amount (DZD)"), max_digits=12, decimal_places=2
    )
    description = models.CharField(
        _("Description"), max_length=500, blank=True
    )
    order = models.ForeignKey(
        "dashboard.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions", verbose_name=_("Order")
    )
    source_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sourced_transactions", verbose_name=_("Source User")
    )
    source_product = models.ForeignKey(
        "dashboard.Product", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transaction_sources", verbose_name=_("Source Product")
    )
    unit_price = models.DecimalField(
        _("Unit Price (DZD)"), max_digits=12, decimal_places=2, null=True, blank=True,
    )
    quantity = models.PositiveIntegerField(
        _("Quantity"), null=True, blank=True,
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=TransactionStatus.choices,
        default=TransactionStatus.COMPLETED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.amount} DZD"
