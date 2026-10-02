"""Shopping lists ("Mon projet"): products chosen for a project, room by room.

A list belongs to the Store. It references products by BPID and keeps the
price seen when each product was added (snapshot) next to the current price,
so nobody is surprised at checkout. A product that changes or disappears is
flagged, never replaced automatically.
"""
import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dashboard.models import Product, ProductItem

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I: easy to read aloud or type


def new_code(length=8):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


class ShoppingList(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SHARED = "shared", _("Shared")
        APPROVED = "approved", _("Approved")
        ORDERED = "ordered", _("Ordered")

    code = models.CharField(_("Code"), max_length=12, unique=True, editable=False)
    edit_key = models.CharField(max_length=40, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="shopping_lists", verbose_name=_("Owner"))
    name = models.CharField(_("Project name"), max_length=120)
    client_name = models.CharField(_("Client"), max_length=120, blank=True)
    budget = models.DecimalField(_("Total budget (DZD)"), max_digits=14, decimal_places=2, null=True, blank=True)
    bilnov_project_id = models.CharField(_("BILNOV project ID"), max_length=64, blank=True)
    status = models.CharField(_("Status"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Shopping list")
        verbose_name_plural = _("Shopping lists")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.code} · {self.name}"

    def save(self, *args, **kwargs):
        if not self.code:
            code = new_code()
            while ShoppingList.objects.filter(code=code).exists():
                code = new_code()
            self.code = code
        if not self.edit_key:
            self.edit_key = secrets.token_urlsafe(24)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shopping:detail", args=[self.code])


class Room(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="rooms")
    name = models.CharField(_("Room"), max_length=80)
    budget = models.DecimalField(_("Budget (DZD)"), max_digits=14, decimal_places=2, null=True, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        ordering = ["position", "pk"]

    def __str__(self):
        return self.name


class ShoppingListItem(models.Model):
    class Status(models.TextChoices):
        PROPOSED_CLIENT = "proposed_client", _("Proposed by the client")
        PROPOSED_ARCHITECT = "proposed_architect", _("Proposed by the architect")
        TO_DISCUSS = "to_discuss", _("To discuss")
        ACCEPTED = "accepted", _("Accepted")
        REFUSED = "refused", _("Refused")
        REPLACED = "replaced", _("Replaced")
        INTEGRATED = "integrated", _("Integrated in the design")
        VALIDATED = "validated", _("Final validation")

    # Lines that no longer count in totals or go to the cart.
    INACTIVE = (Status.REFUSED, Status.REPLACED)

    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="items",
                             verbose_name=_("Room"))
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name="+")
    variant = models.ForeignKey(ProductItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    # What the line pointed to when it was added: kept even if the product is removed from the Store.
    title_snapshot = models.CharField(max_length=255)
    bpid_snapshot = models.CharField(max_length=24, blank=True)
    variant_id_snapshot = models.CharField(max_length=32, blank=True)
    price_snapshot = models.DecimalField(_("Price when added (DZD)"), max_digits=12, decimal_places=2, null=True)
    price_eur_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    snapshot_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.PROPOSED_CLIENT)
    note = models.CharField(_("Note"), max_length=255, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="+")
    replaced_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="replaces")
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("List item")
        verbose_name_plural = _("List items")
        ordering = ["position", "pk"]

    def __str__(self):
        return f"{self.quantity} × {self.title_snapshot}"

    @property
    def counts(self):
        return self.status not in self.INACTIVE

    def availability(self):
        """'available', 'low', 'out_of_stock' or 'unavailable' (removed or no longer sold)."""
        p = self.product
        if p is None or not p.is_active or p.status != Product.ProductStatus.APPROVED:
            return "unavailable"
        if self.variant_id:
            if self.variant is None or not self.variant.is_active:
                return "unavailable"
            stock = self.variant.stock_quantity
        else:
            stock = p.available_stock
        if stock <= 0:
            return "out_of_stock"
        return "low" if stock < self.quantity else "available"
