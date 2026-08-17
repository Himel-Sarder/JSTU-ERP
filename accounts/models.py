"""
Identity, roles and the passkey entry gate.

Every person who touches the ERP has exactly one User row. The role on that row
decides which of the three panels (Student / Teacher / Admin) opens after the
gate is cleared, and RBAC is enforced from there (Proposal section 6).
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    STUDENT = "STUDENT", "Student"
    TEACHER = "TEACHER", "Course Teacher"
    ADMIN = "ADMIN", "Admin / Registrar"


class Designation(models.TextChoices):
    """Sub-role for administrative staff - drives the Admin panel menu."""

    REGISTRAR = "REGISTRAR", "Registrar / Academic Admin"
    EXAM_CONTROLLER = "EXAM_CONTROLLER", "Controller of Examinations"
    ACCOUNTS = "ACCOUNTS", "Accounts Officer"
    PROCTOR = "PROCTOR", "Proctor / Student Affairs Adviser"
    ICT = "ICT", "ICT Cell / System Admin"
    VC = "VC", "Vice-Chancellor / Pro-VC"


class User(AbstractUser):
    """Custom user - e-mail is the identifier used at the passkey gate."""

    email = models.EmailField("e-mail address", unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)
    designation = models.CharField(
        max_length=20, choices=Designation.choices, blank=True,
        help_text="Only for administrative staff.",
    )
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to="avatars/", blank=True, null=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        verbose_name = "user account"
        verbose_name_plural = "user accounts"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        parts = (self.get_full_name() or self.username).split()
        return "".join(p[0] for p in parts[:2]).upper() or "JS"

    @property
    def avatar_url(self):
        """URL of the uploaded photo, or '' when the account has none.

        Reading `photo.url` directly raises when no file is attached, so
        templates use this instead.
        """
        return self.photo.url if self.photo else ""

    @property
    def panel_name(self):
        return {
            Role.STUDENT: "Student Panel",
            Role.TEACHER: "Teacher Panel",
            Role.ADMIN: "Admin / Registrar Panel",
        }.get(self.role, "Portal")

    @property
    def role_label(self):
        if self.role == Role.ADMIN and self.designation:
            return self.get_designation_display()
        return self.get_role_display()


class AccessPasskey(models.Model):
    """
    The 6-digit entry code an administrator issues from the Django admin panel.

    Nobody reaches a panel without presenting a matching e-mail + passkey pair.
    Wrong codes count up and lock the passkey for a cool-down window
    (Proposal section 13 - account lockout on repeated failed logins).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="passkey"
    )
    code = models.CharField(
        "6-digit passkey",
        max_length=6,
        validators=[RegexValidator(r"^\d{6}$", "The passkey must be exactly 6 digits.")],
        help_text="Exactly 6 digits. Share it with the user through an approved channel.",
    )
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(
        blank=True, null=True, help_text="Leave empty for a passkey that never expires."
    )
    failed_attempts = models.PositiveSmallIntegerField(default=0, editable=False)
    locked_until = models.DateTimeField(blank=True, null=True, editable=False)
    last_used_at = models.DateTimeField(blank=True, null=True, editable=False)
    issued_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["user__first_name"]
        verbose_name = "access passkey"
        verbose_name_plural = "access passkeys"

    def __str__(self):
        return f"Passkey for {self.user.email}"

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.now())

    @property
    def status_label(self):
        if not self.is_active:
            return "Disabled"
        if self.is_locked:
            return "Locked"
        if self.is_expired:
            return "Expired"
        return "Active"

    def register_failure(self):
        self.failed_attempts += 1
        if self.failed_attempts >= settings.GATE_MAX_ATTEMPTS:
            self.locked_until = timezone.now() + timedelta(
                minutes=settings.GATE_LOCKOUT_MINUTES
            )
            self.failed_attempts = 0
        self.save(update_fields=["failed_attempts", "locked_until"])

    def register_success(self):
        self.failed_attempts = 0
        self.locked_until = None
        self.last_used_at = timezone.now()
        self.save(update_fields=["failed_attempts", "locked_until", "last_used_at"])

    def attempts_left(self):
        return max(settings.GATE_MAX_ATTEMPTS - self.failed_attempts, 0)


class AuditLog(models.Model):
    """Append-only trail for approvals, gate events and administrative actions."""

    class Action(models.TextChoices):
        GATE_PASS = "GATE_PASS", "Gate cleared"
        GATE_FAIL = "GATE_FAIL", "Gate rejected"
        LOGOUT = "LOGOUT", "Signed out"
        CREATE = "CREATE", "Record created"
        UPDATE = "UPDATE", "Record updated"
        APPROVE = "APPROVE", "Request approved"
        REJECT = "REJECT", "Request rejected"
        PUBLISH = "PUBLISH", "Content published"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    entity = models.CharField(max_length=80, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "audit log entry"
        verbose_name_plural = "audit trail"

    def __str__(self):
        who = self.user.email if self.user else "anonymous"
        return f"{self.get_action_display()} - {who}"

    @classmethod
    def record(cls, request, action, entity="", detail=""):
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        ip = ip or request.META.get("REMOTE_ADDR")
        return cls.objects.create(
            user=request.user if getattr(request.user, "is_authenticated", False) else None,
            action=action,
            entity=entity,
            detail=detail,
            ip_address=ip or None,
        )
