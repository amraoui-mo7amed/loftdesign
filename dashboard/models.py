from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

userModel = get_user_model()

class Notification(models.Model):
    """Notification model for user notifications"""

    class NotificationType(models.TextChoices):
        INFO = "info", _("معلومة")
        SUCCESS = "success", _("نجاح")
        WARNING = "warning", _("تحذير")
        ERROR = "error", _("خطأ")

    user = models.ForeignKey(
        userModel,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("المستخدم"),
        null=True, blank=True
    )
    title = models.CharField(max_length=255, verbose_name=_("العنوان"), null=True, blank=True)
    message = models.TextField(verbose_name=_("الرسالة"), null=True, blank=True)
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        verbose_name=_("نوع الإشعار"),
    )
    is_read = models.BooleanField(default=False, verbose_name=_("مقروء"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("تاريخ الإنشاء"), null=True, blank=True)
    read_at = models.DateTimeField(blank=True, null=True, verbose_name=_("تاريخ القراءة"))
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_("الرابط"),
        help_text=_("رابط اختياري للتنقل"),
    )

    class Meta:
        verbose_name = _("إشعار")
        verbose_name_plural = "الإشعارات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Portfolio(models.Model):
    """Portfolio model for interior design projects"""

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    thumbnail = models.ImageField(upload_to="portfolio/thumbnails/", verbose_name=_("Thumbnail"))
    description = models.TextField(verbose_name=_("Description"))
    tags = models.CharField(max_length=500, verbose_name=_("Tags"), help_text=_("Comma separated tags"))
    img_360 = models.FileField(
        upload_to="portfolio/360_images/", 
        verbose_name=_("360 Degree Image"),
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"), null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Portfolio")
        verbose_name_plural = _("Portfolios")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PortfolioGallery(models.Model):
    """Gallery images for a portfolio project"""

    portfolio = models.ForeignKey(
        Portfolio, 
        on_delete=models.CASCADE, 
        related_name="gallery_images",
        verbose_name=_("Portfolio")
    )
    image = models.ImageField(upload_to="portfolio/gallery/", verbose_name=_("Image"))

    class Meta:
        verbose_name = _("Portfolio Image")
        verbose_name_plural = _("Portfolio Images")

    def __str__(self):
        return f"Image for {self.portfolio.title}"
