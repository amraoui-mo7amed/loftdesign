from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0015_order_referred_by"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE dashboard_order "
                "DROP COLUMN commission_amount, "
                "DROP COLUMN commission_status, "
                "DROP COLUMN parent_commission_amount, "
                "DROP COLUMN affiliate_id, "
                "DROP COLUMN parent_affiliate_id"
            ),
            reverse_sql=(
                "ALTER TABLE dashboard_order "
                "ADD COLUMN commission_amount numeric(12,2) NOT NULL DEFAULT 0, "
                "ADD COLUMN commission_status varchar(20) NOT NULL DEFAULT '', "
                "ADD COLUMN parent_commission_amount numeric(12,2) NOT NULL DEFAULT 0, "
                "ADD COLUMN affiliate_id integer, "
                "ADD COLUMN parent_affiliate_id integer"
            ),
        ),
    ]
