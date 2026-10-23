from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("benchmarks", "0007_algorithmmetric_peak_memory_bytes_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="benchmarkrun",
            name="progress_percent",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benchmarkrun",
            name="progress_message",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="benchmarkrun",
            name="progress_lines_processed",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="benchmarkrun",
            name="progress_total_lines",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
