from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import Attachment, Email, Label, Recipient, User


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "placeholder": "Username",
            "autocomplete": "username",
        })
        self.fields["password"].widget.attrs.update({
            "placeholder": "Password",
            "autocomplete": "current-password",
        })


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "avatar",
            "gender",
            "contact",
            "password1",
            "password2",
        )


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(file, initial) for file in files if file]


class ComposeEmailForm(forms.ModelForm):
    to = forms.CharField(required=False, help_text="Comma-separated usernames or email addresses")
    cc = forms.CharField(required=False, help_text="Comma-separated usernames or email addresses")
    bcc = forms.CharField(required=False, help_text="Comma-separated usernames or email addresses")
    attachments = MultipleFileField(required=False)
    scheduled_at = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        help_text="Choose a future date and time to schedule this email.",
    )

    class Meta:
        model = Email
        fields = ("to", "cc", "bcc", "subject", "body", "scheduled_at", "attachments")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 12}),
        }

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments") or []
        for file in files:
            Attachment(file=file).full_clean(exclude=["email"])
        return files

    def clean(self):
        cleaned_data = super().clean()
        action = self.data.get("action", "draft")
        self.resolved_recipients = {}
        if action in {"send", "schedule"} and not cleaned_data.get("to"):
            self.add_error("to", "Add at least one recipient before sending.")
        if action == "schedule":
            scheduled_at = cleaned_data.get("scheduled_at")
            if not scheduled_at:
                self.add_error("scheduled_at", "Choose when this email should be sent.")
            elif scheduled_at <= timezone.now():
                self.add_error("scheduled_at", "Scheduled time must be in the future.")
        for field_name in ("to", "cc", "bcc"):
            self.resolved_recipients[field_name] = self.resolve_recipients(field_name)
        return cleaned_data

    def resolve_recipients(self, field_name):
        raw_value = self.cleaned_data.get(field_name, "")
        entries = [entry.strip() for entry in raw_value.split(",") if entry.strip()]
        users = []
        missing = []

        for entry in entries:
            user = User.objects.filter(username__iexact=entry).first()
            if user is None:
                user = User.objects.filter(email__iexact=entry).first()
            if user:
                users.append(user)
            else:
                missing.append(entry)

        if missing:
            self.add_error(field_name, f"Unknown recipient: {', '.join(missing)}")
        return users

    def save_email(self, sender, status, parent_email=None, existing_email=None):
        email = existing_email or self.save(commit=False)
        email.sender = sender
        email.subject = self.cleaned_data.get("subject", "")
        email.body = self.cleaned_data.get("body", "")
        email.status = status
        email.scheduled_at = self.cleaned_data.get("scheduled_at") if status == Email.Status.SCHEDULED else None
        if parent_email:
            email.parent_email = parent_email
            email.thread_root = parent_email.thread_root or parent_email
        if status == Email.Status.SENT:
            email.sent_at = timezone.now()
        elif status == Email.Status.SCHEDULED:
            email.sent_at = None
        email.save()

        if existing_email:
            email.recipients.all().delete()

        recipient_map = {
            "to": Recipient.Kind.TO,
            "cc": Recipient.Kind.CC,
            "bcc": Recipient.Kind.BCC,
        }
        for field_name, kind in recipient_map.items():
            for user in self.resolved_recipients.get(field_name, []):
                Recipient.objects.get_or_create(email=email, user=user, kind=kind)

        for file in self.cleaned_data.get("attachments") or []:
            Attachment.objects.create(email=email, file=file)

        return email


class LabelForm(forms.ModelForm):
    class Meta:
        model = Label
        fields = ("name",)
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "New label"}),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter a label name.")
        return name


class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "avatar", "gender", "contact")
        widgets = {
            "email": forms.EmailInput(attrs={"readonly": "readonly", "class": "readonly-input"}),
            "avatar": forms.FileInput(attrs={"class": "visually-hidden", "data-avatar-input": True}),
        }

    def clean_email(self):
        return self.instance.email
