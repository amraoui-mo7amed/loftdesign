from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_auth", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_blocked",
            field=models.BooleanField(default=False, verbose_name="Is Blocked"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="is_trusted",
            field=models.BooleanField(default=False, verbose_name="Is Trusted"),
        ),
    ]
