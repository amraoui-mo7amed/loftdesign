from decimal import Decimal

from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("user_auth", "0009_userprofile_created_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wallet",
            name="balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text=_("Available balance that can be withdrawn"),
                max_digits=12,
                verbose_name=_("Balance (DZD)"),
            ),
        ),
        migrations.AlterField(
            model_name="wallet",
            name="pending_balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text=_("Earnings from orders not yet delivered"),
                max_digits=12,
                verbose_name=_("Pending Balance (DZD)"),
            ),
        ),
    ]
