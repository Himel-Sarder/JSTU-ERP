"""
Passkey gate.

Nothing inside the ERP renders until the visitor has cleared the e-mail +
6-digit passkey screen. The gate itself, the Django admin panel and static or
media files are the only exemptions.
"""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class PasskeyGateMiddleware:
    EXEMPT_PREFIXES = ("/gate", "/admin", "/static", "/media", "/favicon.ico")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        if not path.startswith(self.EXEMPT_PREFIXES):
            cleared = request.session.get(settings.GATE_SESSION_KEY, False)
            if not (cleared and request.user.is_authenticated):
                request.session.flush()
                return redirect(f"{reverse('accounts:gate')}?next={path}")

        return self.get_response(request)
