from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

userModel = get_user_model()

class SiteSettings(models.Model):
    """Global Settings model including home page header slider images"""
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Site Settings")
        verbose_name_plural = _("Site Settings")

    def __str__(self):
        return "Global Site Settings"


class SiteSettingsSliderImage(models.Model):
    """Dynamic Slider Images linked to SiteSettings"""
    settings = models.ForeignKey(
        SiteSettings,
        on_delete=models.CASCADE,
        related_name="slider_images",
        verbose_name=_("Settings")
    )
    image = models.ImageField(upload_to="settings/slider/", verbose_name=_("Slider Image"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Site Settings Slider Image")
        verbose_name_plural = _("Site Settings Slider Images")
        ordering = ["created_at"]

    def __str__(self):
        return f"Slider Image #{self.id}"


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
    tags = models.CharField(max_length=10000, verbose_name=_("Tags"), help_text=_("Comma separated tags"))
    external_link = models.URLField(verbose_name=_("External Link"), blank=True, null=True)
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Featured"))
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


class Category(models.Model):
    """Category model for products"""
    name = models.CharField(max_length=255, verbose_name=_("Category Name"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model with external links for affiliate/direct sales"""

    user = models.ForeignKey(
        userModel,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name=_("User"),
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Category")
    )
    thumbnail = models.ImageField(upload_to="products/thumbnails/", verbose_name=_("Thumbnail"))
    model_3d = models.FileField(
        upload_to="products/models/",
        verbose_name=_("3D Model"),
        blank=True,
        null=True,
        help_text=_("Upload GLB or GLTF 3D model file")
    )
    description = models.TextField(verbose_name=_("Description"))
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Price"), default=0.00)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Available Quantity"))
    external_link = models.URLField(verbose_name=_("External Buy Link"), blank=True, null=True)
    tags = models.CharField(max_length=10000, verbose_name=_("Tags"), blank=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Featured"))
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="gallery_images",
        verbose_name=_("Product")
    )
    image = models.ImageField(upload_to="products/gallery/", verbose_name=_("Image"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        ordering = ["order"]
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")

    def __str__(self):
        return f"{self.product.title} — {self.order}"


class Order(models.Model):
    """Simple order model for lead generation/direct orders"""

    class OrderStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="orders",
        verbose_name=_("Product")
    )
    quantity = models.PositiveIntegerField(
        _("Quantity"), default=1
    )
    customer_name = models.CharField(max_length=255, verbose_name=_("Customer Name"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("Phone Number"))
    customer_address = models.TextField(verbose_name=_("Address"), blank=True)
    wilaya = models.CharField(max_length=100, verbose_name=_("Wilaya"), blank=True)
    commune = models.CharField(max_length=100, verbose_name=_("Commune"), blank=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
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


class Cart(models.Model):
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_("User")
    )
    session_key = models.CharField(
        max_length=40, null=True, blank=True,
        verbose_name=_("Session Key")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        if self.user:
            return f"Cart #{self.id} - {self.user.username}"
        return f"Cart #{self.id} - Session"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items",
        verbose_name=_("Cart")
    )
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE,
        verbose_name=_("Product")
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    class Meta:
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity}x {self.product.title}"

    def subtotal(self):
        return (self.product.price or 0) * self.quantity
