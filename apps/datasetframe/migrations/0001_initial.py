from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("datasets", "0003_dataset_file_size"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatasetFrame",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("model_used", models.CharField(max_length=100)),
                ("result", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="frames",
                        to="datasets.dataset",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dataset Frame",
                "verbose_name_plural": "Dataset Frames",
                "ordering": ["-created_at"],
            },
        ),
    ]
