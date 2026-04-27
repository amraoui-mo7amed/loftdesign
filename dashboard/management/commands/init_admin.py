from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user_auth.models import UserProfile

class Command(BaseCommand):
    help = "Creates a default superuser if it doesn't exist"

    def handle(self, *args, **options):
        username = "admin"
        password = "1234"
        email = "admin@example.com"

        if not User.objects.filter(username=username).exists():
            self.stdout.write(f"Creating superuser {username}...")
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            # Create profile and approve it
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "is_approved": True,
                    "phone_number": "0000000000",
                    "address": "Default Admin Address"
                }
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully created superuser {username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superuser {username} already exists"))
