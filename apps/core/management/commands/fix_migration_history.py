"""
One-time command to record users.0001_initial in django_migrations so that
the account app's swappable_dependency(AUTH_USER_MODEL) is satisfied.

Run once after moving AuthUser from core → users:
    python manage.py fix_migration_history
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Records users.0001_initial in django_migrations to fix inconsistent history"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s",
                ["users", "0001_initial"],
            )
            already_exists = cursor.fetchone()[0] > 0

        if already_exists:
            self.stdout.write("users.0001_initial already recorded — nothing to do.")
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                ["users", "0001_initial", timezone.now()],
            )

        self.stdout.write(self.style.SUCCESS("Recorded users.0001_initial successfully."))
