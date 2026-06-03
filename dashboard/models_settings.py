from django.db import models
from django.utils.translation import gettext_lazy as _

class SiteSettings(models.Model):
    """Global Settings model including home page header slider images"""
    slider_image_1 = models.ImageField(upload_to="settings/slider/", blank=True, null=True, verbose_name=_("Slider Image 1"))
    slider_image_2 = models.ImageField(upload_to="settings/slider/", blank=True, null=True, verbose_name=_("Slider Image 2"))
    slider_image_3 = models.ImageField(upload_to="settings/slider/", blank=True, null=True, verbose_name=_("Slider Image 3"))
    slider_image_4 = models.ImageField(upload_to="settings/slider/", blank=True, null=True, verbose_name=_("Slider Image 4"))
    slider_image_5 = models.ImageField(upload_to="settings/slider/", blank=True, null=True, verbose_name=_("Slider Image 5"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Site Settings")
        verbose_name_plural = _("Site Settings")

    def __str__(self):
        return "Global Site Settings"


class ContactRequest(models.Model):
    """Saves customer contact requests"""
    full_name = models.CharField(max_length=255, verbose_name=_("Full Name"))
    phone_number = models.CharField(max_length=50, verbose_name=_("Phone Number"))
    project_type = models.CharField(max_length=100, verbose_name=_("Project Type"))
    message = models.TextField(verbose_name=_("Message"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Contact Request")
        verbose_name_plural = _("Contact Requests")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contact Request - {self.full_name}"
