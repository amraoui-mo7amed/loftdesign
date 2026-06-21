import datetime
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
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
    """Product model with multi-tier pricing workflow"""

    class ProductStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

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
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Available Quantity"))
    external_link = models.URLField(verbose_name=_("External Buy Link"), blank=True, null=True)
    tags = models.CharField(max_length=10000, verbose_name=_("Tags"), blank=True)
    brand = models.CharField(_("Brand"), max_length=255, blank=True)
    sku = models.CharField(_("SKU"), max_length=100, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Featured"))
    show_in_global_store = models.BooleanField(
        _("Show in Global Store"), default=True,
        help_text=_("Uncheck to hide this product from the public storefront")
    )

    # Pricing Workflow Fields
    status = models.CharField(
        _("Status"), max_length=20, choices=ProductStatus.choices, default=ProductStatus.PENDING
    )
    loft_purchase_price = models.DecimalField(
        _("Purchase Price (DZD)"), max_digits=10, decimal_places=2, default=0.00,
        help_text=_("Price the supplier expects from Loft Design")
    )
    loft_wholesale_price = models.DecimalField(
        _("Wholesale Price (DZD)"), max_digits=10, decimal_places=2, blank=True, null=True,
        help_text=_("Default wholesale price for affiliates (set by admin)")
    )
    loft_retail_price = models.DecimalField(
        _("Retail Price (DZD)"), max_digits=10, decimal_places=2, blank=True, null=True,
        help_text=_("Default retail price for end clients (set by admin)")
    )
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        try:
            qty = int(self.quantity)
        except (ValueError, TypeError):
            qty = 0
        self.is_active = qty > 0 and self.status == self.ProductStatus.APPROVED
        super().save(*args, **kwargs)


class SupplierPrice(models.Model):
    """Supplier's price to Loft Design (one per product)"""
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="supplier_price",
        verbose_name=_("Product")
    )
    supplier = models.ForeignKey(
        userModel, on_delete=models.CASCADE, related_name="supplier_prices",
        verbose_name=_("Supplier")
    )
    loft_purchase_price = models.DecimalField(
        _("Loft Purchase Price (DZD)"), max_digits=10, decimal_places=2,
        help_text=_("Price Loft Design pays the supplier")
    )
    suggested_retail_price = models.DecimalField(
        _("Suggested Retail Price (DZD)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Supplier's suggested retail price")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Supplier Price")
        verbose_name_plural = _("Supplier Prices")

    def __str__(self):
        return f"{self.product.title} — {self.loft_purchase_price} DZD"


class LoftPrice(models.Model):
    """Loft Design's default pricing for a product (one per product)"""
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="loft_price",
        verbose_name=_("Product")
    )
    loft_purchase_price = models.DecimalField(
        _("Loft Purchase Price (DZD)"), max_digits=10, decimal_places=2,
        help_text=_("Copied from supplier price at approval time")
    )
    loft_default_wholesale_price = models.DecimalField(
        _("Default Wholesale Price (DZD)"), max_digits=10, decimal_places=2,
        help_text=_("Default price for affiliates buying from Loft")
    )
    loft_retail_price = models.DecimalField(
        _("Retail Price (DZD)"), max_digits=10, decimal_places=2,
        help_text=_("Public retail price for end clients")
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Loft Price")
        verbose_name_plural = _("Loft Prices")

    def __str__(self):
        return f"{self.product.title} — W:{self.loft_default_wholesale_price} / R:{self.loft_retail_price}"


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


class PartnerPrice(models.Model):
    """Custom negotiated price for a specific seller→buyer pair on a product.
    
    Three price columns allow each level to control their margin:
    - purchase_price: what the buyer pays the seller
    - wholesale_price: what the buyer can resell at (wholesale)
    - retail_price: what the buyer can resell at (retail)
    """
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="partner_prices",
        verbose_name=_("Product")
    )
    seller = models.ForeignKey(
        userModel, on_delete=models.CASCADE, related_name="prices_as_seller",
        verbose_name=_("Seller")
    )
    buyer = models.ForeignKey(
        userModel, on_delete=models.CASCADE, related_name="prices_as_buyer",
        verbose_name=_("Buyer")
    )
    purchase_price = models.DecimalField(
        _("Purchase Price (DZD)"), max_digits=10, decimal_places=2, default=0.00,
        help_text=_("Price the buyer pays the seller")
    )
    wholesale_price = models.DecimalField(
        _("Wholesale Price (DZD)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Price at which buyer can resell (wholesale)")
    )
    retail_price = models.DecimalField(
        _("Retail Price (DZD)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Price at which buyer can resell (retail)")
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Partner Price")
        verbose_name_plural = _("Partner Prices")
        unique_together = ("product", "seller", "buyer")

    def __str__(self):
        return f"{self.product.title} — {self.seller.get_full_name()} → {self.buyer.get_full_name()}: {self.purchase_price}"


class Order(models.Model):
    """Unified order model for both inquiries and cart/checkout orders"""

    class OrderStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        STORE_VALIDATED = "store_validated", _("Validate")
        ADMIN_VALIDATED = "admin_validated", _("Validate")
        SUPPLIER_FULFILLING = "supplier_fulfilling", _("Supplier Fulfilling")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")

    order_number = models.CharField(
        _("Order Number"), max_length=30, unique=True, blank=True, null=True
    )
    buyer = models.ForeignKey(
        userModel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders_as_buyer", verbose_name=_("Buyer")
    )
    seller = models.ForeignKey(
        userModel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders_as_seller", verbose_name=_("Seller")
    )
    items = models.JSONField(
        _("Order Items"),
        default=list,
        blank=True,
        help_text=_("List of products with title, price, quantity, thumbnail at time of order")
    )
    customer_name = models.CharField(max_length=255, verbose_name=_("Customer Name"))
    customer_phone = models.CharField(max_length=20, verbose_name=_("Phone Number"))
    customer_address = models.TextField(verbose_name=_("Address"), blank=True)
    wilaya = models.CharField(max_length=100, verbose_name=_("Wilaya"), blank=True)
    commune = models.CharField(max_length=100, verbose_name=_("Commune"), blank=True)
    referred_by = models.CharField(
        _("Referred By"), max_length=30, blank=True,
        help_text=_("Affiliate code that referred this order")
    )
    commission_paid = models.BooleanField(
        _("Commission Paid"), default=False,
        help_text=_("Whether the affiliate commission for this order has been settled")
    )

    supplier_share = models.DecimalField(
        _("Supplier Share"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Amount paid to supplier for this order")
    )
    loft_share = models.DecimalField(
        _("Loft Share"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Loft Design's profit from this order")
    )
    affiliate_share = models.DecimalField(
        _("Affiliate Share"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Affiliate's profit from this order")
    )
    semi_share = models.DecimalField(
        _("Semi-Affiliate Share"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Semi-affiliate's profit from this order")
    )

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
        on = self.order_number or f"#{self.id}"
        return _("Order %(num)s - %(name)s") % {"num": on, "name": self.customer_name}

    def item_count(self):
        return sum(item.get("quantity", 0) for item in self.items)

    def total_price(self):
        return sum(
            (float(item.get("price", 0)) or 0) * int(item.get("quantity", 1))
            for item in self.items
        )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if not self.order_number:
            dt = timezone.now().strftime("%y%m%d")
            self.order_number = f"ORD-{self.pk}-{dt}"
            super().save(update_fields=["order_number"])


class OrderItem(models.Model):
    """Individual line item within an order"""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_items",
        verbose_name=_("Order")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="order_items", verbose_name=_("Product")
    )
    quantity = models.PositiveIntegerField(_("Quantity"), default=1)
    unit_price = models.DecimalField(
        _("Unit Price (DZD)"), max_digits=10, decimal_places=2,
        help_text=_("Price applied at time of order")
    )
    total_price = models.DecimalField(
        _("Total Price (DZD)"), max_digits=10, decimal_places=2, default=0.00
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    def __str__(self):
        return f"{self.product.title if self.product else 'Deleted product'} x{self.quantity}"


class AffiliateStore(models.Model):
    """Customizable storefront for each affiliate"""
    affiliate = models.OneToOneField(
        "user_auth.UserProfile", on_delete=models.CASCADE, related_name="store",
        verbose_name=_("Affiliate")
    )
    store_name = models.CharField(_("Store Name"), max_length=255, blank=True)
    store_logo = models.ImageField(
        _("Store Logo"), upload_to="stores/logos/", blank=True
    )
    store_banner = models.ImageField(
        _("Store Banner"), upload_to="stores/banners/", blank=True
    )
    store_description = models.TextField(_("Store Description"), blank=True)
    header_bg_color = models.CharField(
        _("Header Background Color"), max_length=7, default="#1a1a2e"
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Affiliate Store")
        verbose_name_plural = _("Affiliate Stores")

    def __str__(self):
        return self.store_name or self.affiliate.affiliate_code or str(self.affiliate)


class StoreVisit(models.Model):
    """Track visits to affiliate storefronts"""
    store = models.ForeignKey(
        AffiliateStore, on_delete=models.CASCADE, related_name="visits",
        verbose_name=_("Store")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="store_visits", verbose_name=_("Product")
    )
    visitor_ip = models.GenericIPAddressField(_("Visitor IP"), blank=True, null=True)
    session_key = models.CharField(_("Session"), max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Store Visit")
        verbose_name_plural = _("Store Visits")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Visit to {self.store} on {self.created_at:%Y-%m-%d}"
