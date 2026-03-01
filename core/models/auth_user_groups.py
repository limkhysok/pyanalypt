from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthUserGroups(models.Model):
    id = models.AutoField(primary_key=True)
    # The column name in the database is 'authuser_id'
    user = models.ForeignKey(
        "AuthUser", on_delete=models.CASCADE, db_column="authuser_id"
    )
    # The column name in the database is 'group_id'
    group = models.ForeignKey(
        "AuthGroup", on_delete=models.CASCADE, db_column="group_id"
    )

    class Meta:
        managed = False
        db_table = "auth_user_groups"
        unique_together = (("user", "group"),)
