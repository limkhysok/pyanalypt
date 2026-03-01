import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def check_table(table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'"
        )
        print(f"Columns for {table_name}: {[c[0] for c in cursor.fetchall()]}")


check_table("auth_user_user_permissions")
check_table("auth_group_permissions")
