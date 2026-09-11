from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Attachment, Email, Label, Recipient, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("DheeMail Profile", {"fields": ("avatar", "gender", "contact")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("DheeMail Profile", {"fields": ("avatar", "gender", "contact")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "gender", "contact", "is_staff")


class RecipientInline(admin.TabularInline):
    model = Recipient
    extra = 0


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender", "status", "created_at", "sent_at")
    list_filter = ("status", "created_at", "sent_at")
    search_fields = ("subject", "body", "sender__username", "sender__email")
    inlines = (RecipientInline, AttachmentInline)


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "kind", "has_read")
    list_filter = ("kind", "has_read")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("email", "file", "uploaded_at")


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__username", "owner__email")
