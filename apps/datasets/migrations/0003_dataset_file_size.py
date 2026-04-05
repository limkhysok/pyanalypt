from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0002_remove_dataset_row_count_and_column_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="file_size",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
