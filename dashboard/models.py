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


class Product(models.Model):
    """Product model with external links for affiliate/direct sales"""

    title = models.CharField(max_length=255, verbose_name=_("Title"))
    thumbnail = models.ImageField(upload_to="products/thumbnails/", verbose_name=_("Thumbnail"))
    description = models.TextField(verbose_name=_("Description"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"), default=0.00)
    external_link = models.URLField(verbose_name=_("External Buy Link"), blank=True, null=True)
    tags = models.CharField(max_length=500, verbose_name=_("Tags"), blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Order(models.Model):
    """Simple order model for lead generation/direct orders"""

    class OrderStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="orders",
        verbose_name=_("Product")
    )
    customer_name = models.CharField(max_length=255, verbose_name=_("Customer Name"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("Phone Number"))
    customer_address = models.TextField(verbose_name=_("Address"), blank=True)
    status = models.CharField(
        max_length=20, 
        choices=OrderStatus.choices, 
        default=OrderStatus.PENDING,
        verbose_name=_("Status")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"
