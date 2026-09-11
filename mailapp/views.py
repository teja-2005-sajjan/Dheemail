from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .forms import AccountForm, ComposeEmailForm, LabelForm, LoginForm, SignupForm
from .models import Email, EmailSnooze, Label, Recipient, User


MAILBOX_PAGE_SIZE = 20


def paginate_emails(request, queryset):
    paginator = Paginator(queryset, MAILBOX_PAGE_SIZE)
    return paginator.get_page(request.GET.get("page"))


def visible_to_user(email, user):
    if email.status == Email.Status.SCHEDULED and email.sender_id != user.id:
        return False
    return email.sender_id == user.id or email.recipients.filter(user=user).exists()


def visible_email_queryset(user):
    return (
        Email.objects.filter(Q(sender=user) | Q(recipients__user=user, status=Email.Status.SENT))
        .exclude(status=Email.Status.DELETED)
        .exclude(deleted_by=user)
        .select_related("sender")
        .distinct()
    )


def redirect_back_or_detail(request, pk):
    next_url = request.POST.get("next_url")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("email_detail", pk=pk)


def redirect_back_or_inbox(request):
    next_url = request.POST.get("next_url")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("inbox")


def display_name(user):
    return user.email or user.username


def is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def release_due_scheduled_emails():
    due_emails = Email.objects.filter(status=Email.Status.SCHEDULED, scheduled_at__lte=timezone.now())
    for email in due_emails:
        email.mark_sent()


def active_snoozed_email_ids(user):
    return EmailSnooze.objects.filter(user=user, snoozed_until__gt=timezone.now()).values_list("email_id", flat=True)


def resolve_user_entries(raw_value):
    entries = [entry.strip() for entry in raw_value.split(",") if entry.strip()]
    users = []
    for entry in entries:
        user = User.objects.filter(username__iexact=entry).first()
        if user is None:
            user = User.objects.filter(email__iexact=entry).first()
        if user and user not in users:
            users.append(user)
    return users


def sync_recipients(email, raw_value, kind):
    email.recipients.filter(kind=kind).delete()
    for user in resolve_user_entries(raw_value):
        Recipient.objects.get_or_create(email=email, user=user, kind=kind)


def prefixed_subject(subject, prefix):
    clean_subject = subject or ""
    if clean_subject.lower().startswith(prefix.lower()):
        return clean_subject
    return f"{prefix} {clean_subject}".strip()


def quoted_body(email):
    sender = email.sender.get_full_name() or display_name(email.sender)
    header = f"\n\nOn {email.sent_at or email.updated_at:%b %d, %Y %H:%M}, {sender} wrote:\n"
    quoted = "\n".join(f"> {line}" for line in email.body.splitlines())
    return header + quoted


def reply_targets(email, user):
    if email.sender_id != user.id:
        return [email.sender]
    return [
        recipient.user
        for recipient in email.recipients.select_related("user")
        if recipient.kind == Recipient.Kind.TO and recipient.user_id != user.id
    ]


def mailbox_context(request, emails, mailbox, title):
    page_obj = paginate_emails(request, emails)
    ids = [email.id for email in page_obj.object_list]
    read_ids = set(
        Recipient.objects.filter(email_id__in=ids, user=request.user, has_read=True).values_list(
            "email_id", flat=True
        )
    )
    starred_ids = set(request.user.starred_emails.filter(id__in=ids).values_list("id", flat=True))
    label_pairs = Label.emails.through.objects.filter(
        email_id__in=ids,
        label__owner=request.user,
    ).values_list("email_id", "label_id")
    labels_by_email = {}
    for email_id, label_id in label_pairs:
        labels_by_email.setdefault(email_id, set()).add(label_id)
    for email in page_obj.object_list:
        email.user_label_ids = labels_by_email.get(email.id, set())
    return {
        "page_obj": page_obj,
        "mailbox": mailbox,
        "mailbox_title": title,
        "read_ids": read_ids,
        "starred_ids": starred_ids,
    }


class CustomLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")
        if remember_me:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        else:
            self.request.session.set_expiry(0)
        return super().form_valid(form)


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to DheeMail.")
            return redirect("dashboard")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    return redirect("inbox")


@login_required
def inbox(request):
    release_due_scheduled_emails()
    emails = (
        Email.objects.filter(recipients__user=request.user, status=Email.Status.SENT)
        .exclude(pk__in=active_snoozed_email_ids(request.user))
        .exclude(deleted_by=request.user)
        .select_related("sender")
        .distinct()
    )
    return render(
        request,
        "mailapp/mailbox.html",
        mailbox_context(request, emails, "inbox", "Inbox"),
    )


@login_required
def sent(request):
    release_due_scheduled_emails()
    emails = (
        Email.objects.filter(sender=request.user, status=Email.Status.SENT)
        .exclude(deleted_by=request.user)
        .select_related("sender")
    )
    return render(
        request,
        "mailapp/mailbox.html",
        mailbox_context(request, emails, "sent", "Sent"),
    )


@login_required
def starred(request):
    release_due_scheduled_emails()
    emails = (
        request.user.starred_emails.exclude(deleted_by=request.user)
        .exclude(status=Email.Status.DELETED)
        .select_related("sender")
        .distinct()
    )
    return render(
        request,
        "mailapp/mailbox.html",
        mailbox_context(request, emails, "starred", "Starred"),
    )


@login_required
def label_mailbox(request, pk):
    release_due_scheduled_emails()
    label = get_object_or_404(Label, pk=pk, owner=request.user)
    emails = (
        label.emails.exclude(deleted_by=request.user)
        .exclude(status=Email.Status.DELETED)
        .select_related("sender")
        .distinct()
    )
    context = mailbox_context(request, emails, f"label-{label.pk}", label.name)
    context["current_label"] = label
    return render(request, "mailapp/mailbox.html", context)


@login_required
def search_emails(request):
    release_due_scheduled_emails()
    query = request.GET.get("q", "").strip()
    if not query:
        return JsonResponse({"results": []})

    emails = visible_email_queryset(request.user).filter(
        Q(subject__icontains=query)
        | Q(body__icontains=query)
        | Q(sender__username__icontains=query)
        | Q(sender__first_name__icontains=query)
        | Q(sender__last_name__icontains=query)
        | Q(sender__email__icontains=query)
    )[:10]
    ids = [email.id for email in emails]
    read_ids = set(
        Recipient.objects.filter(email_id__in=ids, user=request.user, has_read=True).values_list(
            "email_id", flat=True
        )
    )

    results = []
    for email in emails:
        timestamp = email.sent_at or email.updated_at
        sender_name = email.sender.get_full_name() or email.sender.username
        results.append(
            {
                "id": email.id,
                "sender": sender_name,
                "subject": email.subject or "(No subject)",
                "snippet": email.body[:120],
                "time": timestamp.strftime("%b %d, %H:%M"),
                "url": reverse("email_detail", args=[email.pk]),
                "unread": email.sender_id != request.user.id and email.id not in read_ids,
                "starred": email.starred_by.filter(pk=request.user.pk).exists(),
            }
        )

    return JsonResponse({"results": results})


@login_required
def manage_account(request):
    account_form = AccountForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        if request.POST.get("form_type") == "password":
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated.")
                return redirect("manage_account")
        else:
            account_form = AccountForm(request.POST, request.FILES, instance=request.user)
            if account_form.is_valid():
                account_form.save()
                messages.success(request, "Account updated.")
                return redirect("manage_account")

    return render(
        request,
        "mailapp/manage_account.html",
        {"account_form": account_form, "password_form": password_form},
    )


@login_required
def compose(request):
    return compose_email(request)


def compose_email(request, original=None, mode="compose"):
    initial = {}
    title = "New Message"
    if original:
        if mode == "reply":
            initial = {
                "to": ", ".join(dict.fromkeys(display_name(user) for user in reply_targets(original, request.user))),
                "subject": prefixed_subject(original.subject, "Re:"),
                "body": quoted_body(original),
            }
            title = "Reply"
        elif mode == "reply_all":
            to_users = reply_targets(original, request.user)
            cc_users = []
            for recipient in original.recipients.select_related("user"):
                if recipient.user_id == request.user.id or recipient.kind == Recipient.Kind.BCC:
                    continue
                if recipient.kind == Recipient.Kind.TO:
                    to_users.append(recipient.user)
                elif recipient.kind == Recipient.Kind.CC:
                    cc_users.append(recipient.user)
            initial = {
                "to": ", ".join(dict.fromkeys(display_name(user) for user in to_users)),
                "cc": ", ".join(dict.fromkeys(display_name(user) for user in cc_users)),
                "subject": prefixed_subject(original.subject, "Re:"),
                "body": quoted_body(original),
            }
            title = "Reply All"
        elif mode == "forward":
            initial = {
                "subject": prefixed_subject(original.subject, "Fwd:"),
                "body": quoted_body(original),
            }
            title = "Forward"

    if request.method == "POST":
        form = ComposeEmailForm(request.POST, request.FILES)
        action = request.POST.get("action", "draft")
        if action == "send":
            status = Email.Status.SENT
        elif action == "schedule":
            status = Email.Status.SCHEDULED
        else:
            status = Email.Status.DRAFT
        if form.is_valid():
            draft_id = request.POST.get("draft_id")
            existing_draft = None
            if draft_id:
                existing_draft = Email.objects.filter(
                    pk=draft_id,
                    sender=request.user,
                    status=Email.Status.DRAFT,
                ).first()
            form.save_email(request.user, status, parent_email=original, existing_email=existing_draft)
            if status == Email.Status.SENT:
                messages.success(request, "Email sent.")
                return redirect("sent")
            if status == Email.Status.SCHEDULED:
                messages.success(request, "Email scheduled.")
                return redirect("scheduled")
            else:
                messages.success(request, "Draft saved.")
            return redirect("inbox")
    else:
        form = ComposeEmailForm(initial=initial)

    return render(request, "mailapp/compose.html", {"form": form, "compose_title": title, "original": original})


@login_required
def drafts(request):
    emails = Email.objects.filter(sender=request.user, status=Email.Status.DRAFT).exclude(deleted_by=request.user)
    return render(
        request,
        "mailapp/mailbox.html",
        mailbox_context(request, emails, "drafts", "Drafts"),
    )


@login_required
def scheduled(request):
    release_due_scheduled_emails()
    emails = Email.objects.filter(sender=request.user, status=Email.Status.SCHEDULED).exclude(deleted_by=request.user)
    return render(
        request,
        "mailapp/mailbox.html",
        mailbox_context(request, emails, "scheduled", "Scheduled"),
    )


@login_required
def snoozed(request):
    release_due_scheduled_emails()
    snoozes = EmailSnooze.objects.filter(user=request.user, snoozed_until__gt=timezone.now()).select_related("email")
    snooze_map = {snooze.email_id: snooze.snoozed_until for snooze in snoozes}
    emails = (
        Email.objects.filter(pk__in=snooze_map.keys())
        .exclude(status=Email.Status.DELETED)
        .exclude(deleted_by=request.user)
        .select_related("sender")
        .distinct()
    )
    context = mailbox_context(request, emails, "snoozed", "Snoozed")
    for email in context["page_obj"].object_list:
        email.snoozed_until = snooze_map.get(email.pk)
    return render(request, "mailapp/mailbox.html", context)


@login_required
def email_detail(request, pk):
    release_due_scheduled_emails()
    email = get_object_or_404(
        Email.objects.select_related("sender").prefetch_related("recipients__user", "attachments"),
        pk=pk,
    )
    if not visible_to_user(email, request.user) or email.deleted_by.filter(pk=request.user.pk).exists():
        return redirect("inbox")

    recipient = email.recipients.filter(user=request.user).first()
    if recipient and not recipient.has_read:
        recipient.has_read = True
        recipient.save(update_fields=["has_read"])

    recipients = list(email.recipients.select_related("user"))
    if email.sender_id != request.user.id:
        recipients = [
            item
            for item in recipients
            if item.kind != Recipient.Kind.BCC or item.user_id == request.user.id
        ]

    is_starred = email.starred_by.filter(pk=request.user.pk).exists()
    user_recipient = email.recipients.filter(user=request.user).first()
    assigned_label_ids = set(email.labels.filter(owner=request.user).values_list("id", flat=True))
    active_snooze = EmailSnooze.objects.filter(
        email=email,
        user=request.user,
        snoozed_until__gt=timezone.now(),
    ).first()

    return render(
        request,
        "mailapp/email_detail.html",
        {
            "email": email,
            "visible_recipients": recipients,
            "is_starred": is_starred,
            "user_recipient": user_recipient,
            "assigned_label_ids": assigned_label_ids,
            "active_snooze": active_snooze,
        },
    )


@login_required
def snooze_email(request, pk):
    if request.method != "POST":
        return redirect("email_detail", pk=pk)

    email = get_object_or_404(Email, pk=pk)
    if not visible_to_user(email, request.user):
        return redirect("inbox")

    if request.POST.get("clear") == "1":
        EmailSnooze.objects.filter(email=email, user=request.user).delete()
        messages.success(request, "Snooze removed.")
        return redirect_back_or_detail(request, pk)

    raw_value = request.POST.get("snoozed_until", "")
    snoozed_until = parse_datetime(raw_value)
    if snoozed_until and timezone.is_naive(snoozed_until):
        snoozed_until = timezone.make_aware(snoozed_until, timezone.get_current_timezone())

    if not snoozed_until or snoozed_until <= timezone.now():
        messages.error(request, "Choose a future date and time to snooze this email.")
        return redirect_back_or_detail(request, pk)

    EmailSnooze.objects.update_or_create(
        email=email,
        user=request.user,
        defaults={"snoozed_until": snoozed_until},
    )
    messages.success(request, "Email snoozed.")
    return redirect("inbox")


@login_required
def delete_email(request, pk):
    if request.method != "POST":
        return redirect("email_detail", pk=pk)

    email = get_object_or_404(Email, pk=pk)
    if visible_to_user(email, request.user):
        email.deleted_by.add(request.user)
        if email.status == Email.Status.DRAFT and email.sender_id == request.user.id:
            email.status = Email.Status.DELETED
            email.save(update_fields=["status", "updated_at"])
        messages.success(request, "Email deleted.")
        if is_ajax(request):
            return JsonResponse({"deleted": True, "id": email.pk})

    next_mailbox = request.POST.get("next_mailbox", "inbox")
    if next_mailbox == "sent":
        return redirect("sent")
    if next_mailbox == "drafts":
        return redirect("drafts")
    return redirect("inbox")


@login_required
def reply_email(request, pk):
    email = get_object_or_404(Email.objects.prefetch_related("recipients__user"), pk=pk)
    if not visible_to_user(email, request.user):
        return redirect("inbox")
    return compose_email(request, original=email, mode="reply")


@login_required
def reply_all_email(request, pk):
    email = get_object_or_404(Email.objects.prefetch_related("recipients__user"), pk=pk)
    if not visible_to_user(email, request.user):
        return redirect("inbox")
    return compose_email(request, original=email, mode="reply_all")


@login_required
def forward_email(request, pk):
    email = get_object_or_404(Email.objects.prefetch_related("recipients__user"), pk=pk)
    if not visible_to_user(email, request.user):
        return redirect("inbox")
    return compose_email(request, original=email, mode="forward")


@login_required
def toggle_star(request, pk):
    if request.method != "POST":
        return redirect("email_detail", pk=pk)

    email = get_object_or_404(Email, pk=pk)
    starred = False
    if visible_to_user(email, request.user):
        if email.starred_by.filter(pk=request.user.pk).exists():
            email.starred_by.remove(request.user)
        else:
            email.starred_by.add(request.user)
            starred = True
    if is_ajax(request):
        return JsonResponse({"starred": starred, "id": email.pk})
    return redirect_back_or_detail(request, pk)


@login_required
def toggle_read(request, pk):
    if request.method != "POST":
        return redirect("email_detail", pk=pk)

    email = get_object_or_404(Email, pk=pk)
    recipient = email.recipients.filter(user=request.user).first()
    if recipient:
        recipient.has_read = not recipient.has_read
        recipient.save(update_fields=["has_read"])
    return redirect_back_or_detail(request, pk)


@login_required
def create_label(request):
    if request.method != "POST":
        return redirect("inbox")

    form = LabelForm(request.POST)
    if form.is_valid():
        existing = Label.objects.filter(owner=request.user, name__iexact=form.cleaned_data["name"]).first()
        if existing is None:
            Label.objects.create(owner=request.user, name=form.cleaned_data["name"])
        messages.success(request, "Label saved.")
    return redirect_back_or_inbox(request)


@login_required
def delete_label(request, pk):
    if request.method != "POST":
        return redirect("inbox")
    label = get_object_or_404(Label, pk=pk, owner=request.user)
    label.delete()
    messages.success(request, "Label deleted.")
    if is_ajax(request):
        return JsonResponse({"deleted": True, "id": pk})
    return redirect_back_or_inbox(request)


@login_required
def toggle_email_label(request, pk, label_pk):
    if request.method != "POST":
        return redirect("email_detail", pk=pk)

    email = get_object_or_404(Email, pk=pk)
    label = get_object_or_404(Label, pk=label_pk, owner=request.user)
    if visible_to_user(email, request.user):
        if label.emails.filter(pk=email.pk).exists():
            label.emails.remove(email)
            assigned = False
        else:
            label.emails.add(email)
            assigned = True
        if is_ajax(request):
            return JsonResponse({"assigned": assigned, "label": label.name, "id": label.pk})
    return redirect_back_or_detail(request, pk)


@login_required
def autosave_draft(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    draft_id = request.POST.get("draft_id")
    draft = None
    if draft_id:
        draft = Email.objects.filter(pk=draft_id, sender=request.user, status=Email.Status.DRAFT).first()

    if draft is None:
        draft = Email.objects.create(sender=request.user, status=Email.Status.DRAFT)

    draft.subject = request.POST.get("subject", "")
    draft.body = request.POST.get("body", "")
    parent_id = request.POST.get("parent_id")
    if parent_id and not draft.parent_email_id:
        parent = Email.objects.filter(pk=parent_id).first()
        if parent and visible_to_user(parent, request.user):
            draft.parent_email = parent
            draft.thread_root = parent.thread_root or parent
    draft.save(update_fields=["subject", "body", "parent_email", "thread_root", "updated_at"])

    sync_recipients(draft, request.POST.get("to", ""), Recipient.Kind.TO)
    sync_recipients(draft, request.POST.get("cc", ""), Recipient.Kind.CC)
    sync_recipients(draft, request.POST.get("bcc", ""), Recipient.Kind.BCC)

    return JsonResponse({"draft_id": draft.pk, "saved": True})
