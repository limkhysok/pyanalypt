from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthPermission(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    content_type_id = models.IntegerField()  # FK to django_content_type
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "auth_permission"

    def __str__(self):
        return f"{self.content_type_id} | {self.codename}"
