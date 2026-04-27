import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user_auth.models import UserProfile
from django.db import transaction


class Command(BaseCommand):
    help = "Seeds the database with a specified number of randomized users and profiles"

    def add_arguments(self, parser):
        parser.add_argument("count", type=int, help="Number of users to create")

    def handle(self, *args, **kwargs):
        count = kwargs["count"]

        ar_first_names = [
            "محمد",
            "أحمد",
            "ياسين",
            "عمر",
            "إيمان",
            "مريم",
            "ليلى",
            "سمير",
        ]
        ar_last_names = ["بن علي", "بن عمر", "منصوري", "حداد", "بلقاسم", "زروقي"]
        en_first_names = ["John", "Sarah", "Alex", "Emma", "David", "Sophia", "Robert"]
        en_last_names = ["Smith", "Jones", "Williams", "Brown", "Miller", "Davis"]

        bios = [
            "Lover of technology and innovation.",
            "Always exploring new horizons.",
            "Developer by day, gamer by night.",
            "Passionate about clean code and design.",
            "Building the future, one line at a time.",
        ]

        addresses = [
            "Algiers, Algeria",
            "London, UK",
            "New York, USA",
            "Paris, France",
            "Tokyo, Japan",
        ]

        self.stdout.write(f"Seeding {count} users...")

        created_count = 0
        with transaction.atomic():
            for i in range(count):
                lang = random.choice(["ar", "en"])
                if lang == "ar":
                    first = random.choice(ar_first_names)
                    last = random.choice(ar_last_names)
                else:
                    first = random.choice(en_first_names)
                    last = random.choice(en_last_names)

                # Generate a unique username
                base_username = first.lower().replace(" ", "")
                username = f"{base_username}_{random.randint(100, 999)}_{i}"
                email = f"{username}@example.com"

                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{random.randint(100, 9999)}_{i}"

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password="password123",
                    first_name=first,
                    last_name=last,
                )

                sex = random.choice(UserProfile.sexChoices.values)
                approved = random.choice([True, False])
                phone = f"+123{random.randint(10000000, 99999999)}"

                # Randomized birthday (18-60 years ago)
                year = 2024 - random.randint(18, 60)
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                birth_date = f"{year}-{month:02d}-{day:02d}"

                UserProfile.objects.create(
                    user=user,
                    phone_number=phone,
                    sex=sex,
                    bio=random.choice(bios),
                    birth_date=birth_date,
                    address=random.choice(addresses),
                    is_approved=approved,
                )
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} users and profiles."
            )
        )
