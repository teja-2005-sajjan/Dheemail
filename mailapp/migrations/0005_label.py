from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("mailapp", "0004_email_threading_starred"),
    ]

    operations = [
        migrations.CreateModel(
            name="Label",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("emails", models.ManyToManyField(blank=True, related_name="labels", to="mailapp.email")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="labels", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["name"],
                "unique_together": {("owner", "name")},
            },
        ),
    ]
