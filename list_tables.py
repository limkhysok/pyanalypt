import os
import django
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


def list_tables():
    with connection.cursor() as cursor:
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        tables = cursor.fetchall()
        print("Current tables in database:")
        for table in tables:
            print(f"- {table[0]}")


if __name__ == "__main__":
    list_tables()
