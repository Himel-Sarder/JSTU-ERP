"""Shared pages reachable from every panel."""

from django.shortcuts import get_object_or_404, render

from accounts.models import Role
from .models import Notice

PANEL_BASE = {
    Role.STUDENT: "studentpanel/base.html",
    Role.TEACHER: "teacherpanel/base.html",
    Role.ADMIN: "adminpanel/base.html",
}


def notice_detail(request, pk):
    """One notice, rendered inside whichever panel the reader belongs to."""
    notice = get_object_or_404(Notice, pk=pk, is_published=True)
    return render(request, "portal/notice_detail.html", {
        "notice": notice,
        "base_template": PANEL_BASE.get(request.user.role, "studentpanel/base.html"),
        "active": "notices",
        "related": Notice.objects.filter(
            is_published=True, category=notice.category).exclude(pk=notice.pk)[:5],
    })
