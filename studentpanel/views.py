"""Student Panel (Proposal section 7.1)."""

import random
from functools import wraps

from django.contrib import messages
from django.contrib.auth import logout
from django.db.models import Avg, Count, Q  # noqa: F401 - Q used in form builder
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import (YEAR_CHOICES, AdmitCard, ClassRoutine, CourseOffer,
                              Enrollment, EnrollmentDeadline, FeePayment,
                              FormFillup, Marks, Student)
from accounts.models import AuditLog, Role
from portal.models import (Award, ComplaintSuggestion, CourseFeedback, Event,
                           Notice, NoticeDismissal)

from .context_processors import mark_seen


def student_required(view):
    """Only a signed-in student reaches these pages (RBAC, Proposal section 6)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.role != Role.STUDENT:
            messages.error(request, "The Student Panel is only open to student accounts.")
            return redirect("accounts:gate")
        student = Student.objects.filter(user=request.user).select_related(
            "program__department").first()
        if student is None:
            # Give up the gate clearance first. The gate sends a cleared user
            # straight back to their role's panel, so redirecting while still
            # cleared would bounce between the two views forever.
            logout(request)
            messages.error(request, "No student record is linked to this account yet.")
            return redirect("accounts:gate")
        return view(request, student, *args, **kwargs)

    return wrapper


# Bangla ordinals and digits for the printed examination form.
BANGLA_ORDINAL = {1: "১ম", 2: "২য়", 3: "৩য়", 4: "৪র্থ", 5: "৫ম"}
BANGLA_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def deadlines_for(student, open_only=True):
    """Form fill-up windows declared for this student's own cohort.

    A window is matched on degree level, year of study and semester, so a
    4th-year 1st-semester student only ever sees 4th-year 1st-semester
    notices. `Student.level` holds the year of study, which the deadline
    calls `year`.
    """
    windows = EnrollmentDeadline.objects.filter(
        level=student.program.degree_level,
        year=student.level,
        semester=student.semester,
    )
    return windows.filter(is_open=True) if open_only else windows


def shell(student, active, **extra):
    """Context every Student Panel page needs."""
    ctx = {
        "student": student,
        "active": active,
        # Notices this student can still see - hidden ones drop off the badge.
        "notice_count": Notice.objects.filter(
            is_published=True, audience__in=["ALL", "STUDENT"]
        ).exclude(dismissals__student=student).count(),
        # `fillup_alert` (the red dot) comes from
        # studentpanel.context_processors.alerts - it needs the session, which
        # this helper never sees. Setting it here would shadow that value.
    }
    ctx.update(extra)
    return ctx


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@student_required
def dashboard(request, student):
    notices = Notice.objects.filter(
        is_published=True, audience__in=["ALL", "STUDENT"])[:4]
    enrollments = Enrollment.objects.filter(
        student=student, status=Enrollment.Status.ENROLLED
    ).select_related("offer__course", "offer__teacher__user")
    open_deadline = deadlines_for(student).first()
    fillup = FormFillup.objects.filter(student=student).first()
    dues = FormFillup.objects.filter(
        student=student, payment_status=FormFillup.PaymentStatus.UNPAID).count()

    return render(request, "studentpanel/dashboard.html", shell(
        student, "dashboard",
        notices=notices,
        enrollments=enrollments[:5],
        enrolled_total=enrollments.count(),
        events=Event.objects.filter(is_published=True, start_at__gte=timezone.now())[:4],
        open_deadline=open_deadline,
        fillup=fillup,
        dues=dues,
        cgpa=student.cgpa,
        credits=sum(float(e.offer.course.credit) for e in enrollments),
    ))


# --------------------------------------------------------------------------
# Profile & identity
# --------------------------------------------------------------------------
@student_required
def profile(request, student):
    return render(request, "studentpanel/profile.html", shell(student, "profile"))


@student_required
def guardian(request, student):
    if request.method == "POST":
        for field in ["guardian_name", "guardian_relation", "guardian_contact",
                      "guardian_occupation", "contact_no", "present_address",
                      "permanent_address", "blood_group",
                      "name_bn", "father_name", "father_name_bn",
                      "mother_name", "mother_name_bn"]:
            setattr(student, field, request.POST.get(field, "").strip())
        # Only accept a religion from the defined list.
        religion = request.POST.get("religion", "").strip()
        if religion in dict(Student.Religion.choices) or religion == "":
            student.religion = religion
        student.save()
        AuditLog.record(request, AuditLog.Action.UPDATE, "Student", "guardian details")
        messages.success(request, "Guardian and personal details updated.")
        return redirect("studentpanel:guardian")
    return render(request, "studentpanel/guardian.html", shell(
        student, "guardian", religions=Student.Religion.choices))


@student_required
def bank(request, student):
    if request.method == "POST":
        student.bank_name = request.POST.get("bank_name", "").strip()
        student.bank_branch = request.POST.get("bank_branch", "").strip()
        student.bank_account_no = request.POST.get("bank_account_no", "").strip()
        student.save()
        messages.success(request, "Bank account details saved for stipend disbursement.")
        return redirect("studentpanel:bank")
    return render(request, "studentpanel/bank.html", shell(student, "bank"))


@student_required
def id_card(request, student):
    # The card is valid for the nominal length of the programme.
    return render(request, "studentpanel/id_card.html", shell(
        student, "id_card",
        valid_until=student.batch_year + student.program.duration_years,
    ))


@student_required
def network(request, student):
    return render(request, "studentpanel/network.html", shell(student, "network"))


@student_required
def email(request, student):
    return render(request, "studentpanel/email.html", shell(student, "email"))


# --------------------------------------------------------------------------
# Academics
# --------------------------------------------------------------------------
@student_required
def notices(request, student):
    if request.method == "POST":
        notice = get_object_or_404(
            Notice, pk=request.POST.get("notice"),
            is_published=True, audience__in=["ALL", "STUDENT"])
        if request.POST.get("action") == "restore":
            NoticeDismissal.objects.filter(student=student, notice=notice).delete()
            messages.success(request, "Notice restored to your board.")
        else:
            # Hidden for this student only - the notice stays published.
            NoticeDismissal.objects.get_or_create(student=student, notice=notice)
            messages.success(request, "Notice hidden from your board.")
        return redirect("studentpanel:notices")

    mark_seen(request, student)          # opening the board clears the red dot
    hidden_ids = set(NoticeDismissal.objects.filter(student=student)
                     .values_list("notice_id", flat=True))
    showing_hidden = request.GET.get("hidden") == "1"

    qs = Notice.objects.filter(is_published=True, audience__in=["ALL", "STUDENT"])
    category = request.GET.get("category", "")
    if category:
        qs = qs.filter(category=category)
    qs = qs.filter(pk__in=hidden_ids) if showing_hidden else qs.exclude(pk__in=hidden_ids)

    return render(request, "studentpanel/notices.html", shell(
        student, "notices", notices=qs, category=category,
        categories=Notice.Category.choices,
        showing_hidden=showing_hidden, hidden_count=len(hidden_ids),
        # Form fill-up windows declared for this student's cohort, shown at the
        # top of the board so the notice reaches them where they look for news.
        fillup_notices=deadlines_for(student),
        applied_to=set(FormFillup.objects.filter(student=student)
                       .values_list("deadline_id", flat=True)),
    ))


@student_required
def admit_card(request, student):
    cards = AdmitCard.objects.filter(
        student=student, is_released=True).select_related("deadline")
    selected = cards.filter(pk=request.GET.get("card")).first() or cards.first()
    return render(request, "studentpanel/admit_card.html", shell(
        student, "admit_card", cards=cards, card=selected,
        rows=selected.courses if selected else [],
    ))


@student_required
def results(request, student):
    rows = Marks.objects.filter(
        enrollment__student=student, is_published=True
    ).select_related("enrollment__offer__course", "enrollment__offer__teacher__user")

    level = request.GET.get("level", "")
    semester = request.GET.get("semester", "")
    if level:
        rows = rows.filter(enrollment__offer__year=level)
    if semester:
        rows = rows.filter(enrollment__offer__semester=semester)

    credits = sum(float(r.enrollment.offer.course.credit) for r in rows)
    points = sum(float(r.enrollment.offer.course.credit) * float(r.gpa or 0) for r in rows)

    return render(request, "studentpanel/results.html", shell(
        student, "results", rows=rows, level=level, semester=semester,
        gpa=round(points / credits, 2) if credits else 0.00,
        credits=credits, cgpa=student.cgpa,
        levels=range(1, 5), semesters=range(1, 3),
    ))


@student_required
def enrollments(request, student):
    if request.method == "POST":
        offer = get_object_or_404(CourseOffer, pk=request.POST.get("offer"), is_active=True)
        action = request.POST.get("action")
        if action == "cancel":
            Enrollment.objects.filter(student=student, offer=offer).update(
                status=Enrollment.Status.CANCELLED)
            messages.warning(request, f"Enrollment cancelled for {offer.course.course_code}.")
        elif offer.seats_left <= 0:
            messages.error(request, f"{offer.course.course_code} has no seats left.")
        else:
            Enrollment.objects.update_or_create(
                student=student, offer=offer,
                defaults={"status": Enrollment.Status.ENROLLED,
                          "enrollment_date": timezone.localdate()})
            AuditLog.record(request, AuditLog.Action.CREATE, "Enrollment",
                            offer.course.course_code)
            messages.success(request, f"Enrolled in {offer.course.course_code}.")
        return redirect("studentpanel:enrollments")

    mine = Enrollment.objects.filter(student=student).select_related(
        "offer__course", "offer__teacher__user")
    taken = set(mine.filter(status=Enrollment.Status.ENROLLED).values_list("offer_id", flat=True))
    available = CourseOffer.objects.filter(
        # Student.level is the year of study, which the offer now calls `year`.
        is_active=True, year=student.level, semester=student.semester,
        course__department=student.program.department,
    ).exclude(pk__in=taken).select_related("course", "teacher__user")

    return render(request, "studentpanel/enrollments.html", shell(
        student, "enrollments", mine=mine, available=available,
        deadline=deadlines_for(student).first(),
        routine=ClassRoutine.objects.filter(offer_id__in=taken).select_related("offer__course"),
    ))


@student_required
def form_fillup(request, student):
    if request.method == "POST":
        # Look the window up within this student's own cohort, so a posted id
        # from another year or semester can never be applied to. Closed windows
        # stay reachable here, otherwise withdrawing an old application would
        # 404; the apply branch below still checks the window is open.
        deadline = get_object_or_404(
            deadlines_for(student, open_only=False), pk=request.POST.get("deadline"))
        if request.POST.get("action") == "cancel":
            FormFillup.objects.filter(
                student=student, deadline=deadline,
                approval_status=FormFillup.ApprovalStatus.PENDING).delete()
            messages.warning(request, "Form fill-up application withdrawn.")
        else:
            state = deadline.window_state
            if state not in ("Open", "Late window"):
                messages.error(request, f"The form fill-up window is {state.lower()}.")
                return redirect("studentpanel:form_fillup")
            late = state == "Late window"
            amount = deadline.fee_amount + (deadline.late_fee_amount if late else 0)
            FormFillup.objects.get_or_create(
                student=student, deadline=deadline,
                defaults={
                    "invoice_no": f"JSTU-{timezone.now():%Y%m}-{random.randint(10000, 99999)}",
                    "amount": amount, "is_late": late,
                },
            )
            AuditLog.record(request, AuditLog.Action.CREATE, "FormFillup", deadline.exam_title)
            messages.success(request, "Form fill-up submitted. Pay the invoice to continue.")
        return redirect("studentpanel:form_fillup")

    mark_seen(request, student)          # opening the form clears the red dot
    fillups = (FormFillup.objects.filter(student=student)
               .select_related("deadline")
               .prefetch_related("courses__course"))
    # The most recent application - its courses are what the side panel lists.
    current = fillups.first()
    form_courses = list(current.courses.select_related("course")) if current else []
    return render(request, "studentpanel/form_fillup.html", shell(
        student, "form_fillup",
        deadlines=deadlines_for(student),
        fillups=fillups,
        current_form=current,
        form_courses=form_courses,
        total_credit=sum(o.course.credit for o in form_courses),
    ))


@student_required
def form_fillup_action(request, student, pk):
    """The examination form itself - pre-filled, with a course drawer."""
    deadline = get_object_or_404(deadlines_for(student, open_only=False), pk=pk)
    fillup = FormFillup.objects.filter(student=student, deadline=deadline).first()

    if request.method == "POST":
        action = request.POST.get("action")

        # Signature upload / replacement, saved on the student for reuse.
        if action == "signature":
            upload = request.FILES.get("signature")
            if upload:
                if student.signature:
                    student.signature.delete(save=False)
                student.signature = upload
                student.save(update_fields=["signature"])
                messages.success(request, "Signature saved. It will be reused next time.")
            else:
                messages.error(request, "Choose an image of your signature first.")
                return redirect("studentpanel:form_fillup_action", pk=deadline.pk)
            # Falls through, so courses picked before the upload are kept too.

        state = deadline.window_state
        if state not in ("Open", "Late window"):
            messages.error(request, f"The form fill-up window is {state.lower()}.")
            return redirect("studentpanel:form_fillup")

        # Uploading a signature on an untouched form should not raise an
        # invoice; only create one once there is something to record.
        if fillup is None and action == "signature" and not request.POST.getlist("courses"):
            return redirect("studentpanel:form_fillup_action", pk=deadline.pk)

        if fillup is None:
            late = state == "Late window"
            fillup = FormFillup.objects.create(
                student=student, deadline=deadline,
                invoice_no=f"JSTU-{timezone.now():%Y%m}-{random.randint(10000, 99999)}",
                amount=deadline.fee_amount + (deadline.late_fee_amount if late else 0),
                is_late=late,
            )

        # Only offers from this student's own department may be listed.
        picked = request.POST.getlist("courses")
        fillup.courses.set(CourseOffer.objects.filter(
            pk__in=picked, course__department=student.program.department))
        fillup.signed = bool(request.POST.get("include_signature")) and bool(student.signature)
        picked_type = request.POST.get("examinee_type", "")
        if picked_type in dict(FormFillup.ExamineeType.choices) or picked_type == "":
            fillup.examinee_type = picked_type

        if action == "done":
            fillup.is_submitted = True
            fillup.save(update_fields=["signed", "is_submitted", "examinee_type"])
            AuditLog.record(request, AuditLog.Action.CREATE, "FormFillup", deadline.exam_title)
            return redirect("studentpanel:form_fillup_payment", pk=fillup.pk)

        fillup.save(update_fields=["signed", "is_submitted", "examinee_type"])
        if action != "signature":
            messages.success(request, "Form saved. You can come back and finish it later.")
        return redirect("studentpanel:form_fillup_action", pk=deadline.pk)

    # Every offer in the student's department, filtered to year/semester in the
    # drawer by the browser - there are few enough to send at once. Already
    # chosen offers are included even if since deactivated, otherwise a saved
    # row would come back blank.
    chosen_ids = list(fillup.courses.values_list("pk", flat=True)) if fillup else []
    offers = CourseOffer.objects.filter(
        Q(is_active=True) | Q(pk__in=chosen_ids),
        course__department=student.program.department,
    ).select_related("course").order_by("course__course_code")
    catalogue = [{
        "id": o.pk, "code": o.course.course_code, "title": o.course.title,
        "credit": str(o.course.credit), "year": o.year, "semester": o.semester,
    } for o in offers]

    return render(request, "studentpanel/form_fillup_action.html", {
        "student": student, "deadline": deadline, "fillup": fillup,
        "catalogue": catalogue,
        "chosen_ids": chosen_ids,
        "years": YEAR_CHOICES, "semesters": [1, 2, 3],
        "year_bn": BANGLA_ORDINAL.get(deadline.year, deadline.year),
        "semester_bn": BANGLA_ORDINAL.get(deadline.semester, deadline.semester),
        "calendar_year_bn": str(deadline.calendar_year).translate(BANGLA_DIGITS),
    })


@student_required
def form_fillup_payment(request, student, pk):
    fillup = get_object_or_404(FormFillup, pk=pk, student=student)
    return render(request, "studentpanel/form_fillup_payment.html",
                  shell(student, "form_fillup", fillup=fillup))


@student_required
def invoices(request, student):
    if request.method == "POST":
        fillup = get_object_or_404(FormFillup, pk=request.POST.get("fillup"), student=student)
        FeePayment.objects.create(
            form_fillup=fillup, invoice_no=fillup.invoice_no, amount=fillup.amount,
            method=request.POST.get("method", FeePayment.Method.JANATA),
            transaction_id=f"TXN{random.randint(10**9, 10**10 - 1)}",
            status=FeePayment.Status.PENDING,
        )
        fillup.payment_status = FormFillup.PaymentStatus.PAID
        fillup.approval_status = FormFillup.ApprovalStatus.ACCOUNTS
        fillup.save()
        messages.success(request, "Payment submitted. The Accounts Office will verify it shortly.")
        return redirect("studentpanel:invoices")

    fillups = FormFillup.objects.filter(student=student).select_related("deadline")
    return render(request, "studentpanel/invoices.html", shell(
        student, "invoices", fillups=fillups,
        payments=FeePayment.objects.filter(form_fillup__student=student),
        methods=FeePayment.Method.choices,
        outstanding=sum(float(f.amount) for f in fillups
                        if f.payment_status == FormFillup.PaymentStatus.UNPAID),
    ))


# --------------------------------------------------------------------------
# Engagement
# --------------------------------------------------------------------------
@student_required
def complaints(request, student):
    if request.method == "POST":
        anonymous = request.POST.get("is_anonymous") == "on"
        item = ComplaintSuggestion.objects.create(
            student=None if anonymous else student,
            kind=request.POST.get("kind", ComplaintSuggestion.Kind.COMPLAINT),
            report_to=request.POST.get("report_to", ComplaintSuggestion.Office.PROCTOR),
            subject=request.POST.get("subject", "").strip(),
            message=request.POST.get("message", "").strip(),
            is_anonymous=anonymous,
            tracking_code=f"JC-{random.randint(100000, 999999)}",
        )
        messages.success(
            request,
            f"Submitted. Track it with code {item.tracking_code}"
            + (" - your identity was not stored." if anonymous else "."),
        )
        return redirect("studentpanel:complaints")

    return render(request, "studentpanel/complaints.html", shell(
        student, "complaints",
        mine=ComplaintSuggestion.objects.filter(student=student),
        offices=ComplaintSuggestion.Office.choices,
        kinds=ComplaintSuggestion.Kind.choices,
    ))


@student_required
def feedback(request, student):
    enrolled = Enrollment.objects.filter(
        student=student, status=Enrollment.Status.ENROLLED
    ).select_related("offer__course", "offer__teacher__user")

    if request.method == "POST":
        enrollment = get_object_or_404(Enrollment, pk=request.POST.get("enrollment"),
                                       student=student)
        for idx, _ in enumerate(CourseFeedback.QUESTIONS, start=1):
            rating = request.POST.get(f"q{idx}")
            if rating is None:
                continue
            CourseFeedback.objects.update_or_create(
                enrollment=enrollment, question_no=idx,
                defaults={"rating": int(rating),
                          "comment": request.POST.get("comment", "").strip() if idx == 1 else ""},
            )
        messages.success(request, "Thank you. Your feedback was recorded anonymously.")
        return redirect("studentpanel:feedback")

    selected = enrolled.filter(pk=request.GET.get("enrollment")).first() or enrolled.first()
    answered = {}
    if selected:
        answered = {f.question_no: f.rating
                    for f in CourseFeedback.objects.filter(enrollment=selected)}

    questions = [
        (no, text, [(value, label, answered.get(no) == value)
                    for value, label in CourseFeedback.RATING_CHOICES])
        for no, text in enumerate(CourseFeedback.QUESTIONS, start=1)
    ]

    return render(request, "studentpanel/feedback.html", shell(
        student, "feedback", enrolled=enrolled, selected=selected,
        questions=questions,
        done=set(CourseFeedback.objects.filter(enrollment__student=student)
                 .values_list("enrollment_id", flat=True)),
    ))


@student_required
def awards(request, student):
    return render(request, "studentpanel/awards.html", shell(
        student, "awards", awards=Award.objects.filter(student=student)))


@student_required
def support(request, student):
    return render(request, "studentpanel/support.html", shell(student, "support"))
