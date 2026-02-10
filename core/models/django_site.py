from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class DjangoSite(models.Model):
    id = models.AutoField(primary_key=True)
    domain = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "django_site"
