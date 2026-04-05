from django.contrib.auth.models import Permission


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
class AuthPermission(Permission):
    class Meta:
        proxy = True
        # db_table is not needed for proxy models as they use the base model's table

    def __str__(self):
        # Accessing content_type_id from base model
        return f"{self.content_type_id} | {self.codename}"
