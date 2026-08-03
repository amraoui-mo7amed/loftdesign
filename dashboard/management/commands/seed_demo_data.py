import io
import random
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from PIL import Image, ImageDraw

from user_auth.models import UserProfile
from dashboard.models import Category, Product, LoftPrice, SupplierPrice, ProductItem, Notification


class Command(BaseCommand):
    help = "Seeds demo data: provider account, categories, and 5 products (3 admin + 2 provider)"

    COLORS = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400", "#16a085"]

    def _placeholder_image(self, title, color, size=(800, 600)):
        img = Image.new("RGB", size, color)
        draw = ImageDraw.Draw(img)
        draw.text((40, size[1] - 60), title, fill="white")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return ContentFile(buffer.getvalue())

    def _make_image_field(self, file_content, name):
        from django.core.files import File
        field = File(file_content)
        field.name = name
        return field

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stderr.write("No superuser found. Run init_admin first.")
            return

        provider, created = User.objects.get_or_create(
            username="provider",
            defaults={
                "email": "provider@example.com",
                "first_name": "Amine",
                "last_name": "Bennacer",
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created:
            provider.set_password("provider123")
            provider.save()
        profile, _ = UserProfile.objects.get_or_create(
            user=provider,
            defaults={
                "role": UserProfile.roleChoices.PROVIDER,
                "is_approved": True,
                "is_trusted": True,
                "phone_number": "0550123456",
                "address": "Algiers, Algeria",
                "commission": "10.00",
            },
        )

        categories = []
        for name in ["Sofas", "Chairs", "Tables"]:
            cat, _ = Category.objects.get_or_create(name=name)
            categories.append(cat)

        admin_products = [
            {
                "title": "Velvet Lounge Sofa",
                "category": categories[0],
                "description": "Elegant 3-seat velvet sofa with solid wood frame.",
                "loft_purchase_price": "42000.00",
                "loft_wholesale_price": "52000.00",
                "loft_retail_price": "65000.00",
                "quantity": 12,
                "tags": "sofa,velvet,living room",
                "brand": "Loft Home",
                "is_featured": True,
            },
            {
                "title": "Scandinavian Armchair",
                "category": categories[1],
                "description": "Minimalist oak armchair with beige wool upholstery.",
                "loft_purchase_price": "18500.00",
                "loft_wholesale_price": "24000.00",
                "loft_retail_price": "31000.00",
                "quantity": 20,
                "tags": "armchair,scandinavian,oak",
                "brand": "Nordic Craft",
                "is_featured": False,
            },
            {
                "title": "Marble Coffee Table",
                "category": categories[2],
                "description": "Round coffee table with white marble top and brass legs.",
                "loft_purchase_price": "26500.00",
                "loft_wholesale_price": "33000.00",
                "loft_retail_price": "42000.00",
                "quantity": 8,
                "tags": "table,marble,coffee",
                "brand": "Loft Home",
                "is_featured": False,
            },
        ]

        provider_products = [
            {
                "title": "Industrial Metal Chair",
                "category": categories[1],
                "description": "Rustic industrial chair with metal frame and leather seat.",
                "loft_purchase_price": "9800.00",
                "loft_wholesale_price": "13500.00",
                "loft_retail_price": "18000.00",
                "quantity": 30,
                "tags": "chair,industrial,metal",
                "brand": "Urban Steel",
            },
            {
                "title": "Walnut Dining Table",
                "category": categories[2],
                "description": "6-seat dining table in solid walnut with matte finish.",
                "loft_purchase_price": "58000.00",
                "loft_wholesale_price": "70000.00",
                "loft_retail_price": "89000.00",
                "quantity": 5,
                "tags": "dining,table,walnut",
                "brand": "Urban Steel",
            },
        ]

        existing_products = Product.objects.count()
        if existing_products >= 5:
            self.stdout.write(self.style.WARNING("Products already seeded. Skipping product creation."))
        else:
            for data in admin_products:
                self._create_admin_product(admin, data)
            for data in provider_products:
                self._create_provider_product(provider, data, admin)
            self.stdout.write(self.style.SUCCESS("Created 5 products."))

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete. Provider login: {provider.username} / provider123 (trusted={profile.is_trusted})"
            )
        )

    def _create_admin_product(self, admin, data):
        color = random.choice(self.COLORS)
        thumb_name = f"products/thumbnails/{data['title'].replace(' ', '_').lower()}.jpg"
        thumb_field = self._make_image_field(self._placeholder_image(data["title"], color), thumb_name)
        product = Product.objects.create(
            user=admin,
            title=data["title"],
            category=data["category"],
            description=data["description"],
            thumbnail=thumb_field,
            quantity=data["quantity"],
            tags=data["tags"],
            brand=data["brand"],
            is_featured=data["is_featured"],
            is_active=True,
            status=Product.ProductStatus.APPROVED,
            loft_purchase_price=data["loft_purchase_price"],
            loft_wholesale_price=data["loft_wholesale_price"],
            loft_retail_price=data["loft_retail_price"],
            show_in_global_store=True,
            show_in_admin_store=True,
        )
        LoftPrice.objects.get_or_create(
            product=product,
            defaults={
                "loft_purchase_price": data["loft_purchase_price"],
                "loft_default_wholesale_price": data["loft_wholesale_price"],
                "loft_retail_price": data["loft_retail_price"],
                "is_active": True,
            },
        )
        SupplierPrice.objects.get_or_create(
            product=product,
            defaults={
                "supplier": admin,
                "loft_purchase_price": data["loft_purchase_price"],
            },
        )

    def _create_provider_product(self, provider, data, admin):
        color = random.choice(self.COLORS)
        thumb_name = f"products/thumbnails/{data['title'].replace(' ', '_').lower()}.jpg"
        thumb_field = self._make_image_field(self._placeholder_image(data["title"], color), thumb_name)
        product = Product.objects.create(
            user=provider,
            title=data["title"],
            category=data["category"],
            description=data["description"],
            thumbnail=thumb_field,
            quantity=data["quantity"],
            tags=data["tags"],
            brand=data["brand"],
            is_active=False,
            status=Product.ProductStatus.PENDING,
            loft_purchase_price=data["loft_purchase_price"],
            loft_wholesale_price=data["loft_wholesale_price"],
            loft_retail_price=data["loft_retail_price"],
            show_in_global_store=True,
            show_in_admin_store=False,
        )
        Notification.objects.create(
            user=admin,
            title="New Product Requires Validation",
            message=f"{provider.get_full_name() or provider.username} added '{product.title}' — set wholesale/retail prices to activate.",
            notification_type=Notification.NotificationType.INFO,
        )
