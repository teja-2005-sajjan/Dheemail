from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("mailapp", "0003_email_deleted_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="email",
            name="parent_email",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="responses", to="mailapp.email"),
        ),
        migrations.AddField(
            model_name="email",
            name="starred_by",
            field=models.ManyToManyField(blank=True, related_name="starred_emails", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="email",
            name="thread_root",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="thread_messages", to="mailapp.email"),
        ),
    ]
