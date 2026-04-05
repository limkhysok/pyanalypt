from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="dataset",
            name="column_count",
        ),
        migrations.RemoveField(
            model_name="dataset",
            name="row_count",
        ),
    ]
