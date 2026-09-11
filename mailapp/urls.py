from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.CustomLoginView.as_view(), name="login"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("inbox/", views.inbox, name="inbox"),
    path("sent/", views.sent, name="sent"),
    path("starred/", views.starred, name="starred"),
    path("search/", views.search_emails, name="search_emails"),
    path("labels/create/", views.create_label, name="create_label"),
    path("labels/<int:pk>/", views.label_mailbox, name="label_mailbox"),
    path("labels/<int:pk>/delete/", views.delete_label, name="delete_label"),
    path("compose/", views.compose, name="compose"),
    path("compose/autosave/", views.autosave_draft, name="autosave_draft"),
    path("drafts/", views.drafts, name="drafts"),
    path("scheduled/", views.scheduled, name="scheduled"),
    path("snoozed/", views.snoozed, name="snoozed"),
    path("emails/<int:pk>/", views.email_detail, name="email_detail"),
    path("emails/<int:pk>/reply/", views.reply_email, name="reply_email"),
    path("emails/<int:pk>/reply-all/", views.reply_all_email, name="reply_all_email"),
    path("emails/<int:pk>/forward/", views.forward_email, name="forward_email"),
    path("emails/<int:pk>/star/", views.toggle_star, name="toggle_star"),
    path("emails/<int:pk>/read-toggle/", views.toggle_read, name="toggle_read"),
    path("emails/<int:pk>/snooze/", views.snooze_email, name="snooze_email"),
    path("emails/<int:pk>/labels/<int:label_pk>/toggle/", views.toggle_email_label, name="toggle_email_label"),
    path("emails/<int:pk>/delete/", views.delete_email, name="delete_email"),
    path("account/", views.manage_account, name="manage_account"),
]
