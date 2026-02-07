from django.db import models
from django.contrib.contenttypes.models import ContentType

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class DjangoContentType(ContentType):
    class Meta:
        managed = False
        db_table = "django_content_type"
