from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .utils import user_profile_upload_path


class UserProfile(models.Model):
    class roleChoices(models.TextChoices):
        ADMIN = "admin", _("Admin")
        PROVIDER = "provider", _("Provider")

    role = models.CharField(
        _("Role"), max_length=10, choices=roleChoices.choices, default=roleChoices.PROVIDER
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

    # System Fields
    is_approved = models.BooleanField(_("Is Approved"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} Profile"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
