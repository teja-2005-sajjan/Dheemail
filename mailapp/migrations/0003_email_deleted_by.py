from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mailapp", "0002_email_recipient_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="email",
            name="deleted_by",
            field=models.ManyToManyField(blank=True, related_name="deleted_emails", to=settings.AUTH_USER_MODEL),
        ),
    ]
