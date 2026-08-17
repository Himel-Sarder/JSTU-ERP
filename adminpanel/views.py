"""Admin / Registrar Panel (Proposal section 7.3)."""

import random
from functools import wraps

from django.contrib import messages
from django.db.models import Avg, Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import (YEAR_CHOICES, AdmitCard, ClassRoutine, Course,
                              CourseOffer, Department, Enrollment,
                              EnrollmentDeadline, ExamRoutine, FeePayment,
                              FormFillup, Marks, Program, Student, Teacher)
from accounts.models import AccessPasskey, AuditLog, Role, User
from portal.models import (ComplaintSuggestion, CourseFeedback, Event,
                           HouseAllotment, LeaveApplication, Notice,
                           Publication, RequestStatus, VehicleRequisition,
                           WebsiteMenu)


def admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role != Role.ADMIN:
            messages.error(request, "The Admin Panel is only open to administrative accounts.")
            return redirect("accounts:gate")
        return view(request, *args, **kwargs)

    return wrapper


def shell(active, **extra):
    ctx = {
        "active": active,
        "pending_total": FormFillup.objects.filter(
            approval_status__in=[FormFillup.ApprovalStatus.PENDING,
                                 FormFillup.ApprovalStatus.ACCOUNTS]).count(),
        "open_complaints": ComplaintSuggestion.objects.exclude(
            status__in=[ComplaintSuggestion.Status.RESOLVED,
                        ComplaintSuggestion.Status.CLOSED]).count(),
    }
    ctx.update(extra)
    return ctx


# --------------------------------------------------------------------------
@admin_required
def dashboard(request):
    fillups = FormFillup.objects.all()
    S = FormFillup.ApprovalStatus
    return render(request, "adminpanel/dashboard.html", shell(
        "dashboard",
        total_students=Student.objects.filter(status=Student.Status.ACTIVE).count(),
        total_courses=Course.objects.filter(is_active=True).count(),
        total_offers=CourseOffer.objects.filter(is_active=True).count(),
        active_fillups=fillups.count(),
        pending_approvals=fillups.filter(
            approval_status__in=[S.PENDING, S.ACCOUNTS]).count(),
        fillup_active=fillups.count(),
        fillup_pending=fillups.filter(approval_status=S.PENDING).count(),
        fillup_accounts=fillups.filter(approval_status=S.ACCOUNTS).count(),
        fillup_approved=fillups.filter(approval_status=S.APPROVED).count(),
        fillup_final_pending=fillups.filter(approval_status=S.APPROVED).count(),
        notices=Notice.objects.filter(is_published=True)[:5],
        late_requests=fillups.filter(is_late=True,
                                     approval_status=S.PENDING).count(),
        leave_requests=LeaveApplication.objects.filter(
            status=RequestStatus.PENDING).count(),
        house_requests=HouseAllotment.objects.filter(
            status=RequestStatus.PENDING).count(),
        vehicle_requests=VehicleRequisition.objects.filter(
            status=RequestStatus.PENDING).count(),
        complaint_count=ComplaintSuggestion.objects.exclude(
            status__in=[ComplaintSuggestion.Status.RESOLVED,
                        ComplaintSuggestion.Status.CLOSED]).count(),
        faculties=Department.objects.values("faculty_name").distinct().count(),
        departments=Department.objects.count(),
        teachers=Teacher.objects.count(),
        staff=User.objects.filter(role=Role.ADMIN).count(),
    ))


# --------------------------------------------------------------------------
# Curriculum
# --------------------------------------------------------------------------
@admin_required
def add_course(request):
    if request.method == "POST":
        Course.objects.create(
            department_id=request.POST.get("department"),
            course_code=request.POST.get("course_code", "").strip().upper(),
            title=request.POST.get("title", "").strip(),
            category=request.POST.get("category", Course.Category.COMPULSORY),
            course_type=request.POST.get("course_type", Course.Type.THEORY),
            credit=request.POST.get("credit") or 3,
            contact_hour=request.POST.get("contact_hour") or 3,
            year=request.POST.get("year") or 1,
            semester=request.POST.get("semester") or 1,
            description=request.POST.get("description", "").strip(),
        )
        AuditLog.record(request, AuditLog.Action.CREATE, "Course",
                        request.POST.get("course_code", ""))
        messages.success(request, "Course added to the curriculum.")
        return redirect("adminpanel:add_course")

    return render(request, "adminpanel/add_course.html", shell(
        "add_course",
        courses=Course.objects.select_related("department"),
        departments=Department.objects.all(),
        categories=Course.Category.choices,
        types=Course.Type.choices,
    ))


@admin_required
def course_offer(request):
    if request.method == "POST":
        if request.POST.get("action") == "toggle":
            offer = get_object_or_404(CourseOffer, pk=request.POST.get("offer"))
            offer.is_active = not offer.is_active
            offer.save()
            messages.success(request, f"{offer.course.course_code} offer updated.")
        else:
            course = get_object_or_404(Course, pk=request.POST.get("course"))
            CourseOffer.objects.get_or_create(
                course=course,
                level=request.POST.get("level") or Program.Level.BACHELOR,
                year=request.POST.get("year") or course.year,
                semester=request.POST.get("semester") or course.semester,
                calendar_year=request.POST.get("calendar_year") or timezone.now().year,
                defaults={
                    "teacher_id": request.POST.get("teacher") or None,
                    "seat_capacity": request.POST.get("seat_capacity") or 60,
                },
            )
            AuditLog.record(request, AuditLog.Action.CREATE, "CourseOffer",
                            course.course_code)
            messages.success(request, f"{course.course_code} offered to students.")
        return redirect("adminpanel:course_offer")

    return render(request, "adminpanel/course_offer.html", shell(
        "course_offer",
        offers=CourseOffer.objects.select_related("course", "teacher__user"),
        courses=Course.objects.filter(is_active=True),
        teachers=Teacher.objects.select_related("user"),
        levels=Program.Level.choices,
        years=YEAR_CHOICES,
        calendar_year=timezone.now().year,
    ))


@admin_required
def deadline(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "toggle":
            row = get_object_or_404(EnrollmentDeadline, pk=request.POST.get("deadline"))
            row.is_open = not row.is_open
            row.save(update_fields=["is_open"])
            messages.success(request, f"{row.exam_title} window updated.")
            return redirect("adminpanel:deadline")

        if action == "delete":
            row = get_object_or_404(EnrollmentDeadline, pk=request.POST.get("deadline"))
            title = row.exam_title
            applied = row.form_fillups.count()
            if applied:
                # FormFillup protects the window, so refuse with a clear reason
                # rather than letting the database raise.
                messages.error(
                    request,
                    f"\"{title}\" cannot be deleted - {applied} student "
                    f"application{'s' if applied != 1 else ''} reference it. "
                    "Close the window instead.")
                return redirect("adminpanel:deadline")

            cards = row.admit_cards.count()
            try:
                if row.notice_file:
                    row.notice_file.delete(save=False)
                row.delete()
            except ProtectedError:
                messages.error(request, f"\"{title}\" is still referenced and cannot be deleted.")
                return redirect("adminpanel:deadline")

            AuditLog.record(request, AuditLog.Action.UPDATE, "EnrollmentDeadline",
                            f"deleted {title}")
            extra = (f" {cards} admit card{'s' if cards != 1 else ''} removed with it."
                     if cards else "")
            messages.success(request, f"\"{title}\" deleted.{extra}")
            return redirect("adminpanel:deadline")

        # Declare a new window, or save edits to an existing one.
        editing = action == "update"
        row = (get_object_or_404(EnrollmentDeadline, pk=request.POST.get("deadline"))
               if editing else EnrollmentDeadline())

        row.exam_title = request.POST.get("exam_title", "").strip()
        row.level = request.POST.get("level") or Program.Level.BACHELOR
        row.year = request.POST.get("year") or 1
        row.semester = request.POST.get("semester") or 1
        row.calendar_year = request.POST.get("calendar_year") or timezone.now().year
        row.start_date = request.POST.get("start_date")
        row.end_date = request.POST.get("end_date")
        row.late_end_date = request.POST.get("late_end_date") or None
        row.fee_amount = request.POST.get("fee_amount") or 3500
        row.late_fee_amount = request.POST.get("late_fee_amount") or 500
        row.notice = request.POST.get("notice", "").strip()

        # Both optional. A new upload replaces the old file; ticking "remove"
        # clears it; doing neither leaves the existing attachment alone.
        upload = request.FILES.get("notice_file")
        if upload:
            if row.notice_file:
                row.notice_file.delete(save=False)
            row.notice_file = upload
        elif request.POST.get("remove_file") and row.notice_file:
            row.notice_file.delete(save=False)
            row.notice_file = None

        row.save()
        AuditLog.record(request, AuditLog.Action.UPDATE if editing else AuditLog.Action.CREATE,
                        "EnrollmentDeadline", row.exam_title)
        messages.success(request, "Enrollment deadline updated." if editing
                         else "Enrollment deadline declared.")
        return redirect("adminpanel:deadline")

    editing = EnrollmentDeadline.objects.filter(pk=request.GET.get("edit")).first()
    return render(request, "adminpanel/deadline.html", shell(
        "deadline", deadlines=EnrollmentDeadline.objects.all(),
        levels=Program.Level.choices, years=YEAR_CHOICES,
        editing=editing,
        calendar_year=timezone.now().year))


# --------------------------------------------------------------------------
# Examination
# --------------------------------------------------------------------------
@admin_required
def routine(request):
    if request.method == "POST":
        ClassRoutine.objects.create(
            offer_id=request.POST.get("offer"),
            day=request.POST.get("day"),
            start_time=request.POST.get("start_time"),
            end_time=request.POST.get("end_time"),
            room=request.POST.get("room", "").strip(),
        )
        messages.success(request, "Class routine entry published.")
        return redirect("adminpanel:routine")

    return render(request, "adminpanel/routine.html", shell(
        "routine",
        rows=ClassRoutine.objects.select_related("offer__course", "offer__teacher__user"),
        offers=CourseOffer.objects.filter(is_active=True).select_related("course"),
        days=ClassRoutine.Day.choices,
    ))


@admin_required
def exam_schedule(request):
    if request.method == "POST":
        if request.POST.get("action") == "publish":
            row = get_object_or_404(ExamRoutine, pk=request.POST.get("routine"))
            row.is_published = not row.is_published
            row.save()
            AuditLog.record(request, AuditLog.Action.PUBLISH, "ExamRoutine",
                            row.offer.course.course_code)
            messages.success(request, "Exam routine visibility updated.")
        else:
            ExamRoutine.objects.create(
                offer_id=request.POST.get("offer"),
                exam_title=request.POST.get("exam_title", "Semester Final").strip(),
                exam_type=request.POST.get("exam_type", ExamRoutine.ExamType.THEORY),
                exam_date=request.POST.get("exam_date"),
                start_time=request.POST.get("start_time"),
                duration_minutes=request.POST.get("duration_minutes") or 180,
                exam_place=request.POST.get("exam_place", "").strip(),
                memo_no=request.POST.get("memo_no", "").strip(),
            )
            messages.success(request, "Examination scheduled.")
        return redirect("adminpanel:exam_schedule")

    return render(request, "adminpanel/exam_schedule.html", shell(
        "exam_schedule",
        rows=ExamRoutine.objects.select_related("offer__course"),
        offers=CourseOffer.objects.filter(is_active=True).select_related("course"),
        types=ExamRoutine.ExamType.choices,
    ))


@admin_required
def fillup(request):
    S = FormFillup.ApprovalStatus
    if request.method == "POST":
        row = get_object_or_404(FormFillup, pk=request.POST.get("fillup"))
        action = request.POST.get("action")
        if action in dict(S.choices):
            row.approval_status = action
            row.decided_at = timezone.now()
            row.remarks = request.POST.get("remarks", "").strip()
            row.save()
            AuditLog.record(request, AuditLog.Action.APPROVE, "FormFillup", row.invoice_no)
            messages.success(request, f"{row.invoice_no} moved to {row.get_approval_status_display()}.")
        return redirect("adminpanel:fillup")

    rows = FormFillup.objects.select_related("student__user", "deadline")
    state = request.GET.get("state", "")
    if state:
        rows = rows.filter(approval_status=state)

    return render(request, "adminpanel/fillup.html", shell(
        "fillup", rows=rows, state=state, states=S.choices,
        counts={
            "active": FormFillup.objects.count(),
            "pending": FormFillup.objects.filter(approval_status=S.PENDING).count(),
            "accounts": FormFillup.objects.filter(approval_status=S.ACCOUNTS).count(),
            "approved": FormFillup.objects.filter(approval_status=S.APPROVED).count(),
            "final": FormFillup.objects.filter(approval_status=S.FINAL).count(),
            "held": FormFillup.objects.filter(approval_status=S.HELD).count(),
        },
    ))


@admin_required
def student_status(request):
    query = request.GET.get("q", "").strip()
    rows = Student.objects.select_related("user", "program__department")
    if query:
        rows = rows.filter(
            Q(student_id__icontains=query) | Q(registration_no__icontains=query)
            | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
        )
    return render(request, "adminpanel/student_status.html", shell(
        "student_status", rows=rows[:200], query=query,
        fillup_map={f.student_id: f for f in
                    FormFillup.objects.select_related("deadline").order_by("student_id", "-applied_at")},
    ))


@admin_required
def approvals(request):
    S = FormFillup.ApprovalStatus
    if request.method == "POST":
        ids = request.POST.getlist("selected")
        action = request.POST.get("action")
        if ids and action in dict(S.choices):
            FormFillup.objects.filter(pk__in=ids).update(
                approval_status=action, decided_at=timezone.now())
            AuditLog.record(request, AuditLog.Action.APPROVE, "FormFillup",
                            f"{len(ids)} records -> {action}")
            messages.success(request, f"{len(ids)} application(s) updated.")
        return redirect("adminpanel:approvals")

    return render(request, "adminpanel/approvals.html", shell(
        "approvals",
        queue=FormFillup.objects.filter(
            approval_status__in=[S.PENDING, S.ACCOUNTS, S.APPROVED]
        ).select_related("student__user", "deadline"),
        finalized=FormFillup.objects.filter(approval_status=S.FINAL).count(),
    ))


@admin_required
def admit_cards(request):
    if request.method == "POST":
        deadline_obj = get_object_or_404(EnrollmentDeadline, pk=request.POST.get("deadline"))
        action = request.POST.get("action")
        if action == "generate":
            made = 0
            approved = FormFillup.objects.filter(
                deadline=deadline_obj,
                approval_status=FormFillup.ApprovalStatus.FINAL,
            ).select_related("student")
            for row in approved:
                _, created = AdmitCard.objects.get_or_create(
                    student=row.student, deadline=deadline_obj,
                    defaults={"serial_no": f"AC-{deadline_obj.year}-{random.randint(100000, 999999)}"},
                )
                made += int(created)
            messages.success(request, f"{made} admit card(s) generated for {deadline_obj.exam_title}.")
        elif action == "release":
            count = AdmitCard.objects.filter(deadline=deadline_obj).update(is_released=True)
            AuditLog.record(request, AuditLog.Action.PUBLISH, "AdmitCard", deadline_obj.exam_title)
            messages.success(request, f"{count} admit card(s) released to students.")
        return redirect("adminpanel:admit_cards")

    return render(request, "adminpanel/admit_cards.html", shell(
        "admit_cards",
        cards=AdmitCard.objects.select_related("student__user", "deadline"),
        deadlines=EnrollmentDeadline.objects.all(),
        released=AdmitCard.objects.filter(is_released=True).count(),
    ))


@admin_required
def reports(request):
    dept_rows = []
    for dept in Department.objects.all():
        dept_rows.append({
            "dept": dept,
            "students": Student.objects.filter(program__department=dept).count(),
            "teachers": Teacher.objects.filter(department=dept).count(),
            "courses": Course.objects.filter(department=dept).count(),
        })

    grade_rows = (Marks.objects.filter(is_published=True)
                  .values("grade").annotate(n=Count("id")).order_by("-n"))
    collected = FeePayment.objects.filter(
        status=FeePayment.Status.VERIFIED).aggregate(t=Sum("amount"))["t"] or 0
    billed = FormFillup.objects.aggregate(t=Sum("amount"))["t"] or 0

    return render(request, "adminpanel/reports.html", shell(
        "reports", dept_rows=dept_rows, grade_rows=grade_rows,
        collected=collected, billed=billed,
        outstanding=float(billed) - float(collected),
        feedback=CourseFeedback.objects.values(
            "enrollment__offer__teacher__user__first_name",
            "enrollment__offer__teacher__user__last_name",
            "enrollment__offer__course__course_code",
        ).annotate(score=Avg("rating"), n=Count("id")).order_by("-score")[:10],
        publications=Publication.objects.count(),
    ))


# --------------------------------------------------------------------------
# Website & content
# --------------------------------------------------------------------------
@admin_required
def website(request):
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            WebsiteMenu.objects.filter(pk=request.POST.get("menu")).delete()
            messages.warning(request, "Menu removed from the website.")
        else:
            WebsiteMenu.objects.create(
                page_title=request.POST.get("page_title", "").strip(),
                menu_order=request.POST.get("menu_order") or 1,
                external_link=request.POST.get("external_link", "").strip(),
                parent_id=request.POST.get("parent") or None,
                status=request.POST.get("status", WebsiteMenu.Status.PUBLISHED),
                description=request.POST.get("description", "").strip(),
            )
            messages.success(request, "Menu added to the website.")
        return redirect("adminpanel:website")

    return render(request, "adminpanel/website.html", shell(
        "website", menus=WebsiteMenu.objects.select_related("parent"),
        parents=WebsiteMenu.objects.filter(parent__isnull=True),
        statuses=WebsiteMenu.Status.choices,
    ))


@admin_required
def notices(request):
    if request.method == "POST":
        if request.POST.get("action") == "toggle":
            row = get_object_or_404(Notice, pk=request.POST.get("notice"))
            row.is_published = not row.is_published
            row.save()
            messages.success(request, "Notice visibility updated.")
        else:
            Notice.objects.create(
                title=request.POST.get("title", "").strip(),
                category=request.POST.get("category", Notice.Category.UNIVERSITY),
                audience=request.POST.get("audience", Notice.Audience.ALL),
                body=request.POST.get("body", "").strip(),
                posted_by=request.user,
                is_pinned=request.POST.get("is_pinned") == "on",
            )
            AuditLog.record(request, AuditLog.Action.PUBLISH, "Notice",
                            request.POST.get("title", "")[:60])
            messages.success(request, "Notice published.")
        return redirect("adminpanel:notices")

    return render(request, "adminpanel/notices.html", shell(
        "notices", rows=Notice.objects.select_related("posted_by"),
        categories=Notice.Category.choices, audiences=Notice.Audience.choices,
    ))


# --------------------------------------------------------------------------
# Governance
# --------------------------------------------------------------------------
@admin_required
def complaints(request):
    if request.method == "POST":
        row = get_object_or_404(ComplaintSuggestion, pk=request.POST.get("complaint"))
        row.status = request.POST.get("status", row.status)
        row.report_to = request.POST.get("report_to", row.report_to)
        response = request.POST.get("response", "").strip()
        if response:
            row.response = response
        row.save()
        AuditLog.record(request, AuditLog.Action.UPDATE, "ComplaintSuggestion",
                        row.tracking_code)
        messages.success(request, f"{row.tracking_code} updated.")
        return redirect("adminpanel:complaints")

    rows = ComplaintSuggestion.objects.select_related("student__user")
    office = request.GET.get("office", "")
    if office:
        rows = rows.filter(report_to=office)

    return render(request, "adminpanel/complaints.html", shell(
        "complaints", rows=rows, office=office,
        offices=ComplaintSuggestion.Office.choices,
        statuses=ComplaintSuggestion.Status.choices,
    ))


@admin_required
def requests_queue(request):
    if request.method == "POST":
        kind = request.POST.get("kind")
        status = request.POST.get("status")
        model = {"leave": LeaveApplication, "house": HouseAllotment,
                 "vehicle": VehicleRequisition}.get(kind)
        if model and status in dict(RequestStatus.choices):
            row = get_object_or_404(model, pk=request.POST.get("row"))
            row.status = status
            if hasattr(row, "remarks"):
                row.remarks = request.POST.get("remarks", "").strip()
            row.save()
            AuditLog.record(request,
                            AuditLog.Action.APPROVE if status == "APPROVED"
                            else AuditLog.Action.REJECT, model.__name__, str(row))
            messages.success(request, "Request updated.")
        return redirect("adminpanel:requests")

    return render(request, "adminpanel/requests.html", shell(
        "requests",
        leaves=LeaveApplication.objects.select_related("teacher__user"),
        houses=HouseAllotment.objects.select_related("teacher__user"),
        vehicles=VehicleRequisition.objects.select_related("teacher__user"),
    ))


# --------------------------------------------------------------------------
# System
# --------------------------------------------------------------------------
@admin_required
def users(request):
    if request.method == "POST":
        user = get_object_or_404(User, pk=request.POST.get("user"))
        action = request.POST.get("action")
        if action == "issue":
            code = f"{random.randint(0, 999999):06d}"
            AccessPasskey.objects.update_or_create(
                user=user,
                defaults={"code": code, "is_active": True,
                          "failed_attempts": 0, "locked_until": None},
            )
            AuditLog.record(request, AuditLog.Action.UPDATE, "AccessPasskey", user.email)
            messages.success(request, f"New passkey for {user.email}: {code}")
        elif action == "unlock":
            AccessPasskey.objects.filter(user=user).update(
                locked_until=None, failed_attempts=0)
            messages.success(request, f"Passkey unlocked for {user.email}.")
        elif action == "disable":
            AccessPasskey.objects.filter(user=user).update(is_active=False)
            messages.warning(request, f"Passkey disabled for {user.email}.")
        return redirect("adminpanel:users")

    rows = User.objects.select_related("passkey")
    role = request.GET.get("role", "")
    if role:
        rows = rows.filter(role=role)

    return render(request, "adminpanel/users.html", shell(
        "users", rows=rows, role=role,
        roles=[(value, label, User.objects.filter(role=value).count())
               for value, label in Role.choices],
    ))


@admin_required
def audit(request):
    rows = AuditLog.objects.select_related("user")
    action = request.GET.get("action", "")
    if action:
        rows = rows.filter(action=action)
    return render(request, "adminpanel/audit.html", shell(
        "audit", rows=rows[:200], action=action, actions=AuditLog.Action.choices))
