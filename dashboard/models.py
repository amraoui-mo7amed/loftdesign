import datetime
import uuid
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


class Category(models.Model):
    """Category model for products"""
    name = models.CharField(max_length=255, verbose_name=_("Category Name"))
    code = models.CharField(
        _("Bilnov code"), max_length=3, blank=True,
        help_text=_("3-letter category code shared with Bilnov, e.g. FUR (furniture), LGT (lighting), TIL (tiles).")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    """Fabricant d'un produit. Distinct de la marque commerciale et du fournisseur qui vend sur le Store."""
    name = models.CharField(_("Name"), max_length=255)
    manufacturer_id = models.CharField(
        _("Manufacturer ID"), max_length=16, unique=True, null=True, blank=True, editable=False
    )
    country = models.CharField(_("Country"), max_length=100, blank=True)
    website = models.URLField(_("Website"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Manufacturer")
        verbose_name_plural = _("Manufacturers")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.manufacturer_id:
            self.manufacturer_id = f"MFR-{self.pk:05d}"
            type(self).objects.filter(pk=self.pk).update(manufacturer_id=self.manufacturer_id)


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
    # BILNOV Product ID (BPID). Assigned once and never changes, whatever happens to
    # name, price, supplier, images or 3D files. Store, BILNOV, BILNOV Desktop,
    # SketchUp/IFC/GLB files, the 360 viewer, shopping lists, carts and orders refer to it.
    bpid = models.CharField(
        _("BILNOV Product ID (BPID)"), max_length=24, unique=True, null=True, blank=True, editable=False
    )
    manufacturer = models.ForeignKey(
        Manufacturer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products", verbose_name=_("Manufacturer")
    )
    manufacturer_reference = models.CharField(_("Manufacturer reference"), max_length=100, blank=True)
    bilnov_uuid = models.UUIDField(_("Bilnov UUID"), default=uuid.uuid4, unique=True, editable=False)
    collection = models.CharField(_("Collection"), max_length=255, blank=True)
    model_version = models.PositiveIntegerField(
        _("Digital model version"), default=1,
        help_text=_("Increases each time a 3D/BIM file is replaced. Projects keep the version they use.")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Featured"))
    show_in_global_store = models.BooleanField(
        _("Show in Global Store"), default=True,
        help_text=_("Uncheck to hide this product from the public storefront")
    )
    show_in_admin_store = models.BooleanField(
        _("Show in Admin Store"), default=False,
        help_text=_("Check to feature this product in the admin's storefront")
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
    price_eur = models.DecimalField(
        _("Price (EUR, outside Algeria)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Shown to visitors outside Algeria. Leave empty to show the DZD price.")
    )
    pro_price = models.DecimalField(
        _("Professional Price (DZD)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Price for approved professional clients buying directly. Leave empty to use the retail price.")
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def available_stock(self):
        items = self.items.filter(is_active=True)
        if items.exists():
            return sum(items.values_list("stock_quantity", flat=True)) or 0
        return self.quantity or 0

    def save(self, *args, **kwargs):
        try:
            qty = int(self.quantity)
        except (ValueError, TypeError):
            qty = 0
        if self.pk:
            item_stock = sum(self.items.filter(is_active=True).values_list("stock_quantity", flat=True)) or 0
        else:
            item_stock = 0
        effective = qty or item_stock
        self.is_active = effective > 0 and self.status == self.ProductStatus.APPROVED
        super().save(*args, **kwargs)
        if not self.bpid:
            self.bpid = self.build_bpid(self.pk)
            type(self).objects.filter(pk=self.pk, bpid__isnull=True).update(bpid=self.bpid)

    @staticmethod
    def build_bpid(pk):
        """BPID-<9 digits>, e.g. BPID-000002548. Never derived from the name or the category."""
        return f"BPID-{pk:09d}"

    @property
    def supplier_id(self):
        """Fournisseur qui vend le produit sur le Store (compte fournisseur), ex. SUP-00012."""
        return f"SUP-{self.user_id:05d}" if self.user_id else None

    @property
    def store_path(self):
        return f"/store/product/{self.bpid}/"


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
    affiliate_wholesale_price = models.DecimalField(
        _("Affiliate Wholesale Price (DZD)"), max_digits=10, decimal_places=2,
        blank=True, null=True,
        help_text=_("Price the provider charges its own affiliates when reselling this product")
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
    provider_share = models.DecimalField(
        _("Provider Share"), max_digits=12, decimal_places=2, default=0.00,
        help_text=_("Provider's network profit (provider_wholesale - supplier_base) from this order")
    )

    currency = models.CharField(
        _("Currency"), max_length=3, default="DZD",
        help_text=_("Currency shown to the customer (EUR for visitors outside Algeria)")
    )
    total_eur = models.DecimalField(
        _("Total (EUR)"), max_digits=12, decimal_places=2, blank=True, null=True
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
        from decimal import Decimal
        return sum(
            (Decimal(str(item.get("price", 0) or 0)) * int(item.get("quantity", 1)) for item in self.items),
            Decimal("0.00"),
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


class AdminStore(models.Model):
    """Customizable storefront for admin"""
    user = models.OneToOneField(
        userModel, on_delete=models.CASCADE, related_name="admin_store",
        verbose_name=_("Admin")
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
        verbose_name = _("Admin Store")
        verbose_name_plural = _("Admin Stores")

    def __str__(self):
        return self.store_name or self.user.get_full_name() or self.user.username


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


class PriceHistory(models.Model):
    """Tracks changes to wholesale/retail prices across all roles"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_history",
        verbose_name=_("Product")
    )
    user = models.ForeignKey(
        userModel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="price_changes", verbose_name=_("User")
    )
    field_name = models.CharField(
        _("Price Field"), max_length=100,
        help_text=_("e.g. loft_purchase_price, loft_wholesale, loft_retail, partner_wholesale, partner_retail")
    )
    old_value = models.DecimalField(
        _("Old Value (DZD)"), max_digits=10, decimal_places=2, null=True, blank=True
    )
    new_value = models.DecimalField(
        _("New Value (DZD)"), max_digits=10, decimal_places=2
    )
    created_at = models.DateTimeField(_("Changed At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Price History")
        verbose_name_plural = _("Price Histories")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.title[:30]} — {self.field_name}: {self.old_value} → {self.new_value}"


class ProductItem(models.Model):
    """Variant/item of a product with its own media and stock"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="items",
        verbose_name=_("Product")
    )
    name = models.CharField(_("Item Name"), max_length=200)
    # Variant ID = BPID + rank, e.g. BPID-000002548-V02. Permanent like the BPID.
    variant_number = models.PositiveIntegerField(_("Variant number"), null=True, blank=True, editable=False)
    variant_id = models.CharField(_("Variant ID"), max_length=32, unique=True, null=True, blank=True, editable=False)
    sku = models.CharField(
        _("SKU"), max_length=100, unique=True, null=True, blank=True,
        help_text=_("Commercial reference of this variant, e.g. SKU-LUNA-BLK.")
    )
    manufacturer_reference = models.CharField(_("Manufacturer reference"), max_length=100, blank=True)
    color = models.CharField(_("Color"), max_length=100, blank=True)
    dimensions = models.CharField(_("Dimensions"), max_length=200, blank=True)
    thumbnail = models.ImageField(
        _("Thumbnail"), upload_to="product_items/", blank=True
    )
    stock_quantity = models.PositiveIntegerField(_("Stock"), default=0)
    order = models.PositiveIntegerField(_("Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product Item")
        verbose_name_plural = _("Product Items")
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.product.title} — {self.name}"

    def save(self, *args, **kwargs):
        from django.db.models import Max

        if not self.variant_number and self.product_id:
            last = ProductItem.objects.filter(product_id=self.product_id).aggregate(n=Max("variant_number"))["n"] or 0
            self.variant_number = last + 1
        if not self.variant_id and self.variant_number and self.product_id:
            bpid = self.product.bpid or Product.build_bpid(self.product_id)
            self.variant_id = f"{bpid}-V{self.variant_number:02d}"
        super().save(*args, **kwargs)


class ProductItemImage(models.Model):
    """Gallery image for a product item"""
    item = models.ForeignKey(
        ProductItem, on_delete=models.CASCADE, related_name="gallery_images",
        verbose_name=_("Item")
    )
    image = models.ImageField(_("Image"), upload_to="product_items/gallery/")
    order = models.PositiveIntegerField(_("Order"), default=0)

    class Meta:
        verbose_name = _("Item Image")
        verbose_name_plural = _("Item Images")
        ordering = ["order"]

    def __str__(self):
        return f"Image {self.order} for {self.item}"


class ProductAsset(models.Model):
    """Digital file of a catalog product (3D, BIM, CAD, texture, documentation).

    Every file is tied to the product's permanent Bilnov Object ID. Uploading a
    new file of the same format creates a new version; old versions stay
    downloadable so existing projects are never changed behind the architect's back.
    """

    class Format(models.TextChoices):
        SKP = "skp", "SketchUp (SKP)"
        RFA = "rfa", "Revit (RFA)"
        GSM = "gsm", "Archicad (GSM)"
        IFC = "ifc", "IFC"
        GLB = "glb", "GLB / GLTF"
        OBJ = "obj", "OBJ"
        FBX = "fbx", "FBX"
        DWG = "dwg", "DWG"
        TEXTURE = "texture", _("Texture (JPG / PNG / PBR)")
        PDF = "pdf", _("Technical sheet (PDF)")
        OTHER = "other", _("Other")

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="assets",
                                verbose_name=_("Product"))
    variant = models.ForeignKey(ProductItem, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="assets", verbose_name=_("Variant"))
    file_format = models.CharField(_("Format"), max_length=10, choices=Format.choices)
    file = models.FileField(_("File"), upload_to="products/assets/")
    version = models.PositiveIntegerField(_("Version"), default=1, editable=False)
    is_current = models.BooleanField(_("Current version"), default=True, editable=False)
    notes = models.CharField(_("Notes"), max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Product file")
        verbose_name_plural = _("Product files")
        ordering = ["product", "file_format", "-version"]

    def __str__(self):
        return f"{self.product.bpid} {self.file_format} v{self.version}"

    def save(self, *args, **kwargs):
        from django.db import transaction
        from django.db.models import F, Max

        if self.pk:
            return super().save(*args, **kwargs)
        with transaction.atomic():
            same = ProductAsset.objects.select_for_update().filter(
                product=self.product, file_format=self.file_format, variant=self.variant
            )
            last = same.aggregate(v=Max("version"))["v"] or 0
            self.version = last + 1
            same.update(is_current=False)
            super().save(*args, **kwargs)
            if last and self.file_format not in (self.Format.PDF, self.Format.OTHER):
                Product.objects.filter(pk=self.product_id).update(model_version=F("model_version") + 1)
