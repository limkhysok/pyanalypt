from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthUserGroups(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()  # FK to auth_user
    group_id = models.IntegerField()  # FK to auth_group

    class Meta:
        managed = False
        db_table = "auth_user_groups"
