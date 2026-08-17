"""
Entry gate views: e-mail identification, 6-digit passkey verification,
role-based hand-off into the three panels, and sign-out.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import AccessPasskey, AuditLog, Role, User

PANEL_HOME = {
    Role.STUDENT: "studentpanel:dashboard",
    Role.TEACHER: "teacherpanel:dashboard",
    Role.ADMIN: "adminpanel:dashboard",
}


def panel_home_for(user):
    """Where a verified user lands."""
    return reverse(PANEL_HOME.get(user.role, "studentpanel:dashboard"))


def gate(request):
    """The passkey screen shown the moment `manage.py runserver` is opened."""
    if request.session.get(settings.GATE_SESSION_KEY) and request.user.is_authenticated:
        return redirect(panel_home_for(request.user))

    return render(
        request,
        "accounts/gate.html",
        {"next": request.GET.get("next", ""), "digits": range(6)},
    )


def gate_verify(request):
    """Validate e-mail + passkey, then open the matching panel."""
    if request.method != "POST":
        return redirect("accounts:gate")

    email = (request.POST.get("email") or "").strip().lower()
    code = "".join(request.POST.get(f"d{i}", "") for i in range(6)).strip()
    code = code or (request.POST.get("passkey") or "").strip()
    next_url = request.POST.get("next") or ""

    def reject(reason, log_detail=None):
        AuditLog.record(
            request, AuditLog.Action.GATE_FAIL, "AccessPasskey", log_detail or reason
        )
        return render(
            request,
            "accounts/gate.html",
            {"error": reason, "email": email, "next": next_url, "digits": range(6)},
            status=401,
        )

    if not email or len(code) != 6 or not code.isdigit():
        return reject("Enter your university e-mail and the full 6-digit passkey.")

    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return reject(
            "That e-mail and passkey pair did not match. Check with the ICT Cell.",
            f"unknown e-mail: {email}",
        )

    passkey = AccessPasskey.objects.filter(user=user).first()
    if passkey is None or not passkey.is_active:
        return reject(
            "No active passkey is issued for this account. Ask the ICT Cell to issue one.",
            f"no active passkey: {email}",
        )

    if passkey.is_locked:
        return reject(
            f"This passkey is locked for {settings.GATE_LOCKOUT_MINUTES} minutes after "
            "too many wrong codes. Try again later or contact the ICT Cell.",
            f"locked passkey: {email}",
        )

    if passkey.is_expired:
        return reject(
            "This passkey has expired. Request a new one from the ICT Cell.",
            f"expired passkey: {email}",
        )

    if code != passkey.code:
        passkey.register_failure()
        left = passkey.attempts_left()
        note = (
            f" {left} attempt{'s' if left != 1 else ''} left before the passkey locks."
            if left
            else " The passkey is now locked."
        )
        return reject(
            "That e-mail and passkey pair did not match." + note, f"wrong code: {email}"
        )

    # Cleared.
    passkey.register_success()
    login(request, user)
    request.session[settings.GATE_SESSION_KEY] = True
    AuditLog.record(request, AuditLog.Action.GATE_PASS, "AccessPasskey", email)
    messages.success(request, f"Welcome back, {user.display_name}.")

    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(panel_home_for(user))


def sign_out(request):
    if request.user.is_authenticated:
        AuditLog.record(request, AuditLog.Action.LOGOUT, "User", request.user.email)
    logout(request)
    request.session.flush()
    return redirect("accounts:gate")


def switch_account(request):
    """Drop the current session and return to the gate."""
    return sign_out(request)
