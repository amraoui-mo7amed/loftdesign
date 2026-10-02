import uuid

import django.db.models.deletion
from django.db import migrations, models


def assign_identifiers(apps, schema_editor):
    Product = apps.get_model("dashboard", "Product")
    for product in Product.objects.select_related("category").order_by("pk"):
        code = ((product.category.code if product.category_id else "") or "GEN").upper()[:3]
        product.bilnov_uuid = uuid.uuid4()
        product.bilnov_object_id = product.bilnov_object_id or f"BLV-{code}-{product.pk:010d}"
        product.save(update_fields=["bilnov_uuid", "bilnov_object_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0027_eur_and_pro_prices"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="code",
            field=models.CharField(blank=True, help_text="3 letters used in the Bilnov Object ID, e.g. FUR (furniture), LGT (lighting), TIL (tiles).", max_length=3, verbose_name="Bilnov code"),
        ),
        migrations.AddField(
            model_name="product",
            name="bilnov_object_id",
            field=models.CharField(blank=True, editable=False, max_length=32, null=True, unique=True, verbose_name="Bilnov Object ID"),
        ),
        migrations.AddField(
            model_name="product",
            name="bilnov_uuid",
            field=models.UUIDField(editable=False, null=True, verbose_name="Bilnov UUID"),
        ),
        migrations.AddField(
            model_name="product",
            name="collection",
            field=models.CharField(blank=True, max_length=255, verbose_name="Collection"),
        ),
        migrations.AddField(
            model_name="product",
            name="model_version",
            field=models.PositiveIntegerField(default=1, help_text="Increases each time a 3D/BIM file is replaced. Projects keep the version they use.", verbose_name="Digital model version"),
        ),
        migrations.AddField(
            model_name="productitem",
            name="sku",
            field=models.CharField(blank=True, help_text="Commercial reference of this variant, e.g. SKU-LUNA-BLK.", max_length=100, null=True, unique=True, verbose_name="SKU"),
        ),
        migrations.RunPython(assign_identifiers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="product",
            name="bilnov_uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Bilnov UUID"),
        ),
        migrations.CreateModel(
            name="ProductAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file_format", models.CharField(choices=[("skp", "SketchUp (SKP)"), ("rfa", "Revit (RFA)"), ("gsm", "Archicad (GSM)"), ("ifc", "IFC"), ("glb", "GLB / GLTF"), ("obj", "OBJ"), ("fbx", "FBX"), ("dwg", "DWG"), ("texture", "Texture (JPG / PNG / PBR)"), ("pdf", "Technical sheet (PDF)"), ("other", "Other")], max_length=10, verbose_name="Format")),
                ("file", models.FileField(upload_to="products/assets/", verbose_name="File")),
                ("version", models.PositiveIntegerField(default=1, editable=False, verbose_name="Version")),
                ("is_current", models.BooleanField(default=True, editable=False, verbose_name="Current version")),
                ("notes", models.CharField(blank=True, max_length=255, verbose_name="Notes")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assets", to="dashboard.product", verbose_name="Product")),
                ("variant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assets", to="dashboard.productitem", verbose_name="Variant")),
            ],
            options={
                "verbose_name": "Product file",
                "verbose_name_plural": "Product files",
                "ordering": ["product", "file_format", "-version"],
            },
        ),
    ]
