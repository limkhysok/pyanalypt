"""
Remove AuthUser from core's migration state now that it lives in the 'users'
app.  No database operations — the auth_user table is untouched.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_authuser_email_alter_authuser_username'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel('AuthUser'),
            ],
            database_operations=[],
        ),
    ]
