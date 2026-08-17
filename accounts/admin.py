"""
Django admin panel - this is where the administrator issues the entry passkeys.
"""

import random

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import AccessPasskey, AuditLog, User

admin.site.site_header = "JSTU ERP Control Centre"
admin.site.site_title = "JSTU ERP"
admin.site.index_title = "Jamalpur Science and Technology University"


class PasskeyInline(admin.StackedInline):
    model = AccessPasskey
    can_delete = False
    extra = 0
    fields = ("code", "is_active", "valid_until", "note", "status_readout")
    readonly_fields = ("status_readout",)
    verbose_name_plural = "Entry passkey (6 digits)"

    @admin.display(description="Status")
    def status_readout(self, obj):
        if not obj.pk:
            return "-"
        return format_html(
            "<b>{}</b> &nbsp;|&nbsp; failed attempts: {} &nbsp;|&nbsp; last used: {}",
            obj.status_label,
            obj.failed_attempts,
            obj.last_used_at.strftime("%d %b %Y, %I:%M %p") if obj.last_used_at else "never",
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [PasskeyInline]
    list_display = ("email", "get_full_name", "role", "designation", "passkey_state", "is_active")
    list_filter = ("role", "designation", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("JSTU role", {"fields": ("role", "designation", "phone", "photo")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "first_name", "last_name",
                       "role", "designation", "password1", "password2"),
        }),
    )
    actions = ["issue_passkey", "disable_passkey", "unlock_passkey"]

    @admin.display(description="Passkey")
    def passkey_state(self, obj):
        pk_obj = getattr(obj, "passkey", None)
        if not pk_obj:
            return format_html('<span style="color:#b91c1c">not issued</span>')
        colour = {"Active": "#15803d", "Locked": "#b45309"}.get(pk_obj.status_label, "#b91c1c")
        return format_html(
            '<code>{}</code> <span style="color:{}">({})</span>',
            pk_obj.code, colour, pk_obj.status_label,
        )

    @admin.action(description="Issue / regenerate a 6-digit entry passkey")
    def issue_passkey(self, request, queryset):
        lines = []
        for user in queryset:
            code = f"{random.randint(0, 999999):06d}"
            AccessPasskey.objects.update_or_create(
                user=user,
                defaults={"code": code, "is_active": True,
                          "failed_attempts": 0, "locked_until": None},
            )
            lines.append(f"{user.email} -> {code}")
        self.message_user(
            request, "Passkeys issued: " + "; ".join(lines), messages.SUCCESS
        )

    @admin.action(description="Disable the entry passkey")
    def disable_passkey(self, request, queryset):
        count = AccessPasskey.objects.filter(user__in=queryset).update(is_active=False)
        self.message_user(request, f"{count} passkey(s) disabled.", messages.WARNING)

    @admin.action(description="Unlock the entry passkey")
    def unlock_passkey(self, request, queryset):
        count = AccessPasskey.objects.filter(user__in=queryset).update(
            locked_until=None, failed_attempts=0
        )
        self.message_user(request, f"{count} passkey(s) unlocked.", messages.SUCCESS)


@admin.register(AccessPasskey)
class AccessPasskeyAdmin(admin.ModelAdmin):
    list_display = ("user", "code", "status_label", "failed_attempts",
                    "valid_until", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("failed_attempts", "locked_until", "last_used_at", "issued_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "entity", "detail", "ip_address")
    list_filter = ("action", "created_at")
    search_fields = ("detail", "entity", "user__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False
