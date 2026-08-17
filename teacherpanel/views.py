"""Teacher Panel (Proposal section 7.2)."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from academics.models import (ClassRoutine, CourseOffer, Enrollment, ExamRoutine,
                              Marks, Teacher)
from accounts.models import AuditLog, Role
from portal.models import (CourseFeedback, Event, ExamRemuneration,
                           HouseAllotment, LeaveApplication, Notice,
                           PostgraduateApplication, Publication, RequestStatus,
                           ResearchPost, VehicleRequisition)


def teacher_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role != Role.TEACHER:
            messages.error(request, "The Teacher Panel is only open to faculty accounts.")
            return redirect("accounts:gate")
        teacher = Teacher.objects.filter(user=request.user).select_related(
            "department").first()
        if teacher is None:
            # Give up the gate clearance first. The gate sends a cleared user
            # straight back to their role's panel, so redirecting while still
            # cleared would bounce between the two views forever.
            logout(request)
            messages.error(request, "No faculty record is linked to this account yet.")
            return redirect("accounts:gate")
        return view(request, teacher, *args, **kwargs)

    return wrapper


def as_local(value):
    """Turn a naive ``datetime-local`` string into an Asia/Dhaka aware datetime."""
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def shell(teacher, active, **extra):
    pending = (
        LeaveApplication.objects.filter(teacher=teacher,
                                        status=RequestStatus.PENDING).count()
        + PostgraduateApplication.objects.filter(supervisor=teacher,
                                                 status=RequestStatus.PENDING).count()
    )
    ctx = {"teacher": teacher, "active": active, "pending_total": pending}
    ctx.update(extra)
    return ctx


def current_offers(teacher):
    return CourseOffer.objects.filter(teacher=teacher, is_active=True).select_related("course")


# --------------------------------------------------------------------------
@teacher_required
def dashboard(request, teacher):
    offers = current_offers(teacher)
    enrolled = Enrollment.objects.filter(offer__in=offers,
                                         status=Enrollment.Status.ENROLLED)
    unpublished = Marks.objects.filter(enrollment__offer__in=offers,
                                       is_published=False).count()
    pending_leaves = LeaveApplication.objects.filter(
        teacher=teacher, status=RequestStatus.PENDING).count()
    pending_pg = PostgraduateApplication.objects.filter(
        supervisor=teacher, status=RequestStatus.PENDING).count()

    today = timezone.localdate()
    day_key = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][today.weekday()]

    return render(request, "teacherpanel/dashboard.html", shell(
        teacher, "dashboard",
        offers=offers,
        offer_rows=[(o, o.enrolled_count) for o in offers],
        course_count=offers.count(),
        student_count=enrolled.values("student").distinct().count(),
        pending_tasks=unpublished + pending_leaves + pending_pg,
        unpublished=unpublished,
        pending_leaves=pending_leaves,
        pending_pg=pending_pg,
        today_classes=ClassRoutine.objects.filter(
            offer__in=offers, day=day_key).select_related("offer__course"),
        notices=Notice.objects.filter(is_published=True,
                                      audience__in=["ALL", "TEACHER"])[:5],
        events=Event.objects.filter(start_at__gte=timezone.now(), is_published=True)[:4],
    ))


# --------------------------------------------------------------------------
@teacher_required
def profile(request, teacher):
    return render(request, "teacherpanel/profile.html", shell(
        teacher, "profile",
        offers=current_offers(teacher),
        publications=Publication.objects.filter(teacher=teacher).count(),
        feedback_avg=CourseFeedback.objects.filter(
            enrollment__offer__teacher=teacher).aggregate(a=Avg("rating"))["a"],
    ))


@teacher_required
def marks(request, teacher):
    offers = current_offers(teacher)
    selected = offers.filter(pk=request.GET.get("offer")).first() or offers.first()

    if request.method == "POST":
        offer = get_object_or_404(CourseOffer, pk=request.POST.get("offer"), teacher=teacher)
        publish = request.POST.get("action") == "publish"
        saved = 0
        for enrollment in Enrollment.objects.filter(offer=offer,
                                                    status=Enrollment.Status.ENROLLED):
            prefix = f"e{enrollment.pk}_"
            row, _ = Marks.objects.get_or_create(enrollment=enrollment)
            for field in ("attendance_marks", "ct_marks", "final_marks"):
                value = request.POST.get(prefix + field)
                if value not in (None, ""):
                    setattr(row, field, value)
            repeat = request.POST.get(prefix + "repeat_final_marks")
            row.repeat_final_marks = repeat if repeat else None
            if publish:
                row.is_published = True
            row.save()
            saved += 1
        AuditLog.record(request, AuditLog.Action.PUBLISH if publish else AuditLog.Action.UPDATE,
                        "Marks", offer.course.course_code)
        messages.success(
            request,
            f"{saved} record{'s' if saved != 1 else ''} saved"
            + (" and published to students." if publish else "."),
        )
        return redirect(f"{request.path}?offer={offer.pk}")

    rows = []
    if selected:
        for enrollment in Enrollment.objects.filter(
            offer=selected, status=Enrollment.Status.ENROLLED
        ).select_related("student__user"):
            row, _ = Marks.objects.get_or_create(enrollment=enrollment)
            rows.append((enrollment, row))

    return render(request, "teacherpanel/marks.html", shell(
        teacher, "marks", offers=offers, selected=selected, rows=rows))


@teacher_required
def pg_marks(request, teacher):
    if request.method == "POST":
        app = get_object_or_404(PostgraduateApplication,
                                pk=request.POST.get("application"), supervisor=teacher)
        action = request.POST.get("action")
        if action in ("APPROVED", "REJECTED"):
            app.status = action
        thesis = request.POST.get("thesis_marks")
        if thesis:
            app.thesis_marks = thesis
        app.save()
        messages.success(request, f"Application {app.research_title[:30]} updated.")
        return redirect("teacherpanel:pg_marks")

    return render(request, "teacherpanel/pg_marks.html", shell(
        teacher, "pg_marks",
        applications=PostgraduateApplication.objects.filter(
            supervisor=teacher).select_related("student__user"),
    ))


@teacher_required
def class_routine(request, teacher):
    return render(request, "teacherpanel/class_routine.html", shell(
        teacher, "class_routine",
        days=ClassRoutine.Day.choices,
        routine=ClassRoutine.objects.filter(
            offer__teacher=teacher).select_related("offer__course"),
    ))


@teacher_required
def exam_routine(request, teacher):
    return render(request, "teacherpanel/exam_routine.html", shell(
        teacher, "exam_routine",
        routines=ExamRoutine.objects.filter(
            offer__teacher=teacher).select_related("offer__course"),
    ))


@teacher_required
def students(request, teacher):
    offers = current_offers(teacher)
    selected = offers.filter(pk=request.GET.get("offer")).first() or offers.first()
    query = request.GET.get("q", "").strip()

    roster = Enrollment.objects.none()
    if selected:
        roster = Enrollment.objects.filter(
            offer=selected, status=Enrollment.Status.ENROLLED
        ).select_related("student__user", "marks")
        if query:
            roster = roster.filter(
                Q(student__student_id__icontains=query)
                | Q(student__user__first_name__icontains=query)
                | Q(student__user__last_name__icontains=query)
            )

    return render(request, "teacherpanel/students.html", shell(
        teacher, "students", offers=offers, selected=selected, roster=roster, query=query))


# --------------------------------------------------------------------------
@teacher_required
def leave(request, teacher):
    if request.method == "POST":
        LeaveApplication.objects.create(
            teacher=teacher,
            leave_type=request.POST.get("leave_type", LeaveApplication.LeaveType.CASUAL),
            from_date=request.POST.get("from_date"),
            to_date=request.POST.get("to_date"),
            reason=request.POST.get("reason", "").strip(),
            address_during_leave=request.POST.get("address_during_leave", "").strip(),
        )
        AuditLog.record(request, AuditLog.Action.CREATE, "LeaveApplication", teacher.employee_id)
        messages.success(request, "Leave application submitted to the Registrar's Office.")
        return redirect("teacherpanel:leave")

    return render(request, "teacherpanel/leave.html", shell(
        teacher, "leave",
        applications=LeaveApplication.objects.filter(teacher=teacher),
        leave_types=LeaveApplication.LeaveType.choices,
    ))


@teacher_required
def house(request, teacher):
    if request.method == "POST":
        HouseAllotment.objects.create(
            teacher=teacher,
            house_category=request.POST.get("house_category", HouseAllotment.Category.D),
            preferred_quarter=request.POST.get("preferred_quarter", "").strip(),
            family_members=request.POST.get("family_members") or 1,
            reason=request.POST.get("reason", "").strip(),
        )
        messages.success(request, "House allotment request submitted.")
        return redirect("teacherpanel:house")

    return render(request, "teacherpanel/house.html", shell(
        teacher, "house",
        requests=HouseAllotment.objects.filter(teacher=teacher),
        categories=HouseAllotment.Category.choices,
    ))


@teacher_required
def vehicle(request, teacher):
    if request.method == "POST":
        VehicleRequisition.objects.create(
            teacher=teacher,
            vehicle_type=request.POST.get("vehicle_type", VehicleRequisition.Vehicle.MICROBUS),
            purpose=request.POST.get("purpose", "").strip(),
            destination=request.POST.get("destination", "").strip(),
            journey_date=request.POST.get("journey_date"),
            return_date=request.POST.get("return_date") or None,
            passengers=request.POST.get("passengers") or 1,
        )
        messages.success(request, "Vehicle requisition submitted to the Transport Office.")
        return redirect("teacherpanel:vehicle")

    return render(request, "teacherpanel/vehicle.html", shell(
        teacher, "vehicle",
        requests=VehicleRequisition.objects.filter(teacher=teacher),
        vehicles=VehicleRequisition.Vehicle.choices,
    ))


@teacher_required
def events(request, teacher):
    if request.method == "POST":
        Event.objects.create(
            title=request.POST.get("title", "").strip(),
            kind=request.POST.get("kind", Event.Kind.SEMINAR),
            organizer=teacher,
            venue=request.POST.get("venue", "").strip(),
            start_at=as_local(request.POST.get("start_at")),
            end_at=as_local(request.POST.get("end_at")),
            description=request.POST.get("description", "").strip(),
        )
        messages.success(request, "Event published to the university calendar.")
        return redirect("teacherpanel:events")

    return render(request, "teacherpanel/events.html", shell(
        teacher, "events",
        events=Event.objects.filter(organizer=teacher),
        upcoming=Event.objects.filter(start_at__gte=timezone.now(), is_published=True)[:6],
        kinds=Event.Kind.choices,
    ))


# --------------------------------------------------------------------------
@teacher_required
def research(request, teacher):
    if request.method == "POST":
        ResearchPost.objects.create(
            teacher=teacher,
            title=request.POST.get("title", "").strip(),
            category=request.POST.get("category", "Research news").strip(),
            body=request.POST.get("body", "").strip(),
        )
        messages.success(request, "Post published to the research feed.")
        return redirect("teacherpanel:research")

    return render(request, "teacherpanel/research.html", shell(
        teacher, "research", posts=ResearchPost.objects.filter(teacher=teacher)))


@teacher_required
def publications(request, teacher):
    if request.method == "POST":
        Publication.objects.create(
            teacher=teacher,
            title=request.POST.get("title", "").strip(),
            authors=request.POST.get("authors", "").strip(),
            journal_name=request.POST.get("journal_name", "").strip(),
            kind=request.POST.get("kind", Publication.Kind.JOURNAL),
            year=request.POST.get("year") or timezone.now().year,
            indexing=request.POST.get("indexing", "").strip(),
            doi_link=request.POST.get("doi_link", "").strip(),
            in_baures=request.POST.get("in_baures") == "on",
        )
        messages.success(request, "Publication recorded.")
        return redirect("teacherpanel:publications")

    rows = Publication.objects.filter(teacher=teacher)
    return render(request, "teacherpanel/publications.html", shell(
        teacher, "publications", publications=rows, kinds=Publication.Kind.choices,
        journal_count=rows.filter(kind=Publication.Kind.JOURNAL).count(),
        conference_count=rows.filter(kind=Publication.Kind.CONFERENCE).count(),
    ))


@teacher_required
def remuneration(request, teacher):
    rows = ExamRemuneration.objects.filter(teacher=teacher)
    return render(request, "teacherpanel/remuneration.html", shell(
        teacher, "remuneration", rows=rows,
        total=sum(float(r.amount) for r in rows),
        paid=sum(float(r.amount) for r in rows if r.status == ExamRemuneration.Status.PAID),
    ))


@teacher_required
def baures(request, teacher):
    return render(request, "teacherpanel/baures.html", shell(
        teacher, "baures",
        listed=Publication.objects.filter(teacher=teacher, in_baures=True),
        unlisted=Publication.objects.filter(teacher=teacher, in_baures=False),
    ))


@teacher_required
def notices(request, teacher):
    return render(request, "teacherpanel/notices.html", shell(
        teacher, "notices",
        notices=Notice.objects.filter(is_published=True,
                                      audience__in=["ALL", "TEACHER"]),
    ))
