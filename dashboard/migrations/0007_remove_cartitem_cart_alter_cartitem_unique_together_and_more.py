from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_productimage'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CartItem',
        ),
        migrations.DeleteModel(
            name='Cart',
        ),
    ]
