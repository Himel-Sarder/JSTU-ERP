"""Red-dot alerts for the Student Panel menu.

This lives in a context processor rather than in `shell()` because it needs the
request session: the dot is cleared by visiting the Notice board or the Form
fill-up page, and `shell()` never sees the request.
"""

from accounts.models import Role

SEEN_KEY = "fillup_seen"


def alerts(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or user.role != Role.STUDENT:
        return {}

    # Imported here to keep module import order simple.
    from academics.models import Student
    from .views import deadlines_for

    student = Student.objects.filter(user=user).select_related("program").first()
    if student is None:
        return {}

    outstanding = set(
        deadlines_for(student)
        .exclude(form_fillups__student=student)
        .values_list("pk", flat=True)
    )
    seen = set(request.session.get(SEEN_KEY, []))
    # A window declared after the last visit is unseen again, so the dot returns.
    return {"fillup_alert": bool(outstanding - seen)}


def mark_seen(request, student):
    """Called when the student opens the Notice board or Form fill-up page."""
    from .views import deadlines_for

    seen = set(request.session.get(SEEN_KEY, []))
    seen |= set(deadlines_for(student).values_list("pk", flat=True))
    request.session[SEEN_KEY] = sorted(seen)
