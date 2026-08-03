from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0015_order_referred_by"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE dashboard_order "
                "DROP COLUMN IF EXISTS commission_amount, "
                "DROP COLUMN IF EXISTS commission_status, "
                "DROP COLUMN IF EXISTS parent_commission_amount, "
                "DROP COLUMN IF EXISTS affiliate_id, "
                "DROP COLUMN IF EXISTS parent_affiliate_id"
            ),
            reverse_sql=(
                "ALTER TABLE dashboard_order "
                "ADD COLUMN IF NOT EXISTS commission_amount numeric(12,2) NOT NULL DEFAULT 0, "
                "ADD COLUMN IF NOT EXISTS commission_status varchar(20) NOT NULL DEFAULT '', "
                "ADD COLUMN IF NOT EXISTS parent_commission_amount numeric(12,2) NOT NULL DEFAULT 0, "
                "ADD COLUMN IF NOT EXISTS affiliate_id integer, "
                "ADD COLUMN IF NOT EXISTS parent_affiliate_id integer"
            ),
        ),
    ]
