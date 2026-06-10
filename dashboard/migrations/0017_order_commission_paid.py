from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0016_remove_orphan_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="commission_paid",
            field=models.BooleanField(
                default=False,
                help_text="Whether the affiliate commission for this order has been settled",
                verbose_name="Commission Paid",
            ),
        ),
    ]
