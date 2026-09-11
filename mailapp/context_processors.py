from django.utils import timezone

from .forms import LabelForm
from .models import Email, EmailSnooze, Label, Recipient


def mail_sidebar(request):
    if not request.user.is_authenticated:
        return {}

    unread_count = (
        Recipient.objects.filter(user=request.user, has_read=False)
        .filter(email__status=Email.Status.SENT)
        .exclude(
            email_id__in=EmailSnooze.objects.filter(
                user=request.user,
                snoozed_until__gt=timezone.now(),
            ).values_list("email_id", flat=True)
        )
        .exclude(email__deleted_by=request.user)
        .distinct()
        .count()
    )

    return {
        "sidebar_unread_count": unread_count,
        "sidebar_labels": Label.objects.filter(owner=request.user),
        "sidebar_label_form": LabelForm(),
    }
