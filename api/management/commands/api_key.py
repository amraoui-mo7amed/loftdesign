from django.core.management.base import BaseCommand, CommandError

from api.models import ApiClient


class Command(BaseCommand):
    help = "Create, list or revoke Store API keys (BILNOV, BILNOV Desktop, plugins)."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["create", "list", "revoke"])
        parser.add_argument("name", nargs="?", help="client name (create) or key prefix (revoke)")

    def handle(self, action, name=None, **options):
        if action == "create":
            if not name:
                raise CommandError('Give a name, e.g. api_key create "BILNOV Desktop"')
            client, raw = ApiClient.create(name)
            self.stdout.write(f"{client.name}\n{raw}\nKeep this key now: it will not be shown again.")
        elif action == "list":
            for c in ApiClient.objects.order_by("created_at"):
                self.stdout.write(f"{c.prefix}  {'active ' if c.is_active else 'revoked'}  {c.name}")
        else:
            n = ApiClient.objects.filter(prefix=name).update(is_active=False)
            if not n:
                raise CommandError("Unknown prefix")
            self.stdout.write("Revoked.")
