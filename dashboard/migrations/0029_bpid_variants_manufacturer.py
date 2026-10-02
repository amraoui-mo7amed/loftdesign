import django.db.models.deletion
from django.db import migrations, models


def assign_bpid_and_variants(apps, schema_editor):
    Product = apps.get_model("dashboard", "Product")
    ProductItem = apps.get_model("dashboard", "ProductItem")
    for product in Product.objects.order_by("pk"):
        product.bpid = f"BPID-{product.pk:09d}"
        product.save(update_fields=["bpid"])
        for n, item in enumerate(ProductItem.objects.filter(product=product).order_by("order", "created_at", "pk"), start=1):
            item.variant_number = n
            item.variant_id = f"{product.bpid}-V{n:02d}"
            item.save(update_fields=["variant_number", "variant_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0028_bilnov_object_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="Manufacturer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                ("manufacturer_id", models.CharField(blank=True, editable=False, max_length=16, null=True, unique=True, verbose_name="Manufacturer ID")),
                ("country", models.CharField(blank=True, max_length=100, verbose_name="Country")),
                ("website", models.URLField(blank=True, verbose_name="Website")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Manufacturer", "verbose_name_plural": "Manufacturers", "ordering": ["name"]},
        ),
        migrations.RenameField(model_name="product", old_name="bilnov_object_id", new_name="bpid"),
        migrations.AlterField(
            model_name="product",
            name="bpid",
            field=models.CharField(blank=True, editable=False, max_length=24, null=True, unique=True, verbose_name="BILNOV Product ID (BPID)"),
        ),
        migrations.AddField(
            model_name="product",
            name="manufacturer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="products", to="dashboard.manufacturer", verbose_name="Manufacturer"),
        ),
        migrations.AddField(
            model_name="product",
            name="manufacturer_reference",
            field=models.CharField(blank=True, max_length=100, verbose_name="Manufacturer reference"),
        ),
        migrations.AlterField(
            model_name="category",
            name="code",
            field=models.CharField(blank=True, help_text="3-letter category code shared with Bilnov, e.g. FUR (furniture), LGT (lighting), TIL (tiles).", max_length=3, verbose_name="Bilnov code"),
        ),
        migrations.AddField(
            model_name="productitem",
            name="variant_number",
            field=models.PositiveIntegerField(blank=True, editable=False, null=True, verbose_name="Variant number"),
        ),
        migrations.AddField(
            model_name="productitem",
            name="variant_id",
            field=models.CharField(blank=True, editable=False, max_length=32, null=True, unique=True, verbose_name="Variant ID"),
        ),
        migrations.AddField(
            model_name="productitem",
            name="manufacturer_reference",
            field=models.CharField(blank=True, max_length=100, verbose_name="Manufacturer reference"),
        ),
        migrations.RunPython(assign_bpid_and_variants, migrations.RunPython.noop),
    ]
