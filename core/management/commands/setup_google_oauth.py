"""
Django management command to set up Google OAuth configuration.

Usage:
    python manage.py setup_google_oauth
"""

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings
import environ

env = environ.Env()


class Command(BaseCommand):
    help = "Set up Google OAuth configuration from environment variables"

    def handle(self, *args, **options):
        self.stdout.write("Setting up Google OAuth...")

        # Get or create the site
        site, created = Site.objects.get_or_create(
            id=settings.SITE_ID if hasattr(settings, "SITE_ID") else 1,
            defaults={
                "domain": "localhost:8000",
                "name": "PyAnalypt (Development)",
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created site: {site.domain}"))
        else:
            self.stdout.write(f"  Site already exists: {site.domain}")

        # Get Google credentials from environment
        client_id = env("GOOGLE_CLIENT_ID", default=None)
        client_secret = env("GOOGLE_CLIENT_SECRET", default=None)

        if not client_id or not client_secret:
            self.stdout.write(
                self.style.ERROR(
                    "✗ Google OAuth credentials not found in .env file!\n"
                    "  Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
                )
            )
            return

        # Create or update Google OAuth app
        google_app, created = SocialApp.objects.get_or_create(
            provider="google",
            defaults={
                "name": "Google",
                "client_id": client_id,
                "secret": client_secret,
            },
        )

        if not created:
            # Update existing app
            google_app.client_id = client_id
            google_app.secret = client_secret
            google_app.save()
            self.stdout.write("  Google app already exists, updated credentials")
        else:
            self.stdout.write(self.style.SUCCESS("✓ Created Google OAuth app"))

        # Link the app to the site
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Linked Google app to {site.domain}")
            )
        else:
            self.stdout.write(f"  Google app already linked to {site.domain}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("✓ Google OAuth setup complete!"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"\nGoogle Client ID: {client_id[:20]}...")
        self.stdout.write(f"Site: {site.domain}")
        self.stdout.write(
            "\nYou can now use Google OAuth at:\n"
            "  • Web: http://localhost:8000/accounts/google/login/\n"
            "  • API: POST http://localhost:8000/api/v1/auth/google/\n"
        )
