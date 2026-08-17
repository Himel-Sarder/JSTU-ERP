"""
Shared and cross-cutting records (Proposal section 7.4) plus the engagement,
teacher self-service and research modules.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from academics.models import Enrollment, Student, Teacher


# --------------------------------------------------------------------------
# Communication
# --------------------------------------------------------------------------
class Notice(models.Model):
    class Category(models.TextChoices):
        UNIVERSITY = "UNIVERSITY", "University"
        DEPARTMENT = "DEPARTMENT", "Department"
        EXAM = "EXAM", "Examination"
        ACCOUNTS = "ACCOUNTS", "Accounts"
        EVENT = "EVENT", "Event"

    class Audience(models.TextChoices):
        ALL = "ALL", "Everyone"
        STUDENT = "STUDENT", "Students"
        TEACHER = "TEACHER", "Teachers"
        ADMIN = "ADMIN", "Administration"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=12, choices=Category.choices,
                                default=Category.UNIVERSITY)
    audience = models.CharField(max_length=8, choices=Audience.choices, default=Audience.ALL)
    body = models.TextField(blank=True)
    attachment = models.FileField(upload_to="notices/", blank=True, null=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name="notices")
    post_date = models.DateField(default=timezone.now)
    is_published = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_pinned", "-post_date", "-id"]

    def __str__(self):
        return self.title


class NoticeDismissal(models.Model):
    """One student hiding one notice from their own board.

    Nothing is deleted - the notice stays published for everyone else, and the
    student can restore it from the hidden list.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE,
                                related_name="notice_dismissals")
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE,
                               related_name="dismissals")
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "notice")
        ordering = ["-dismissed_at"]
        verbose_name = "notice dismissal"

    def __str__(self):
        return f"{self.student.student_id} hid {self.notice.title[:40]}"


class WebsiteMenu(models.Model):
    """Website Control Panel -> Add Menu (Proposal section 7.3)."""

    class Status(models.TextChoices):
        PUBLISHED = "PUBLISHED", "Published"
        DRAFT = "DRAFT", "Draft"

    page_title = models.CharField(max_length=120)
    menu_order = models.PositiveSmallIntegerField(default=1)
    external_link = models.URLField(blank=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, blank=True, null=True,
                               related_name="children", verbose_name="parent menu")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PUBLISHED)
    description = models.TextField(blank=True, help_text="Rich-text page body.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["menu_order", "page_title"]
        verbose_name = "website menu"

    def __str__(self):
        return self.page_title


# --------------------------------------------------------------------------
# Student engagement
# --------------------------------------------------------------------------
class ComplaintSuggestion(models.Model):
    class Office(models.TextChoices):
        VC = "VC", "Vice-Chancellor"
        REGISTRAR = "REGISTRAR", "Registrar"
        PROCTOR = "PROCTOR", "Proctor"
        LIBRARIAN = "LIBRARIAN", "Librarian"
        ACCOUNTS = "ACCOUNTS", "Accounts Officer"
        ICT = "ICT", "ICT Cell"

    class Kind(models.TextChoices):
        COMPLAINT = "COMPLAINT", "Complaint"
        SUGGESTION = "SUGGESTION", "Suggestion"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        ROUTED = "ROUTED", "Routed"
        IN_REVIEW = "IN_REVIEW", "In review"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="complaints",
                                help_text="Left empty when submitted anonymously.")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.COMPLAINT)
    report_to = models.CharField(max_length=10, choices=Office.choices, default=Office.PROCTOR)
    subject = models.CharField(max_length=160)
    message = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    response = models.TextField(blank=True)
    tracking_code = models.CharField(max_length=14, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "complaint / suggestion"
        verbose_name_plural = "complaints & suggestions"

    def __str__(self):
        return f"{self.tracking_code} - {self.subject}"

    @property
    def submitted_by(self):
        """Identity is not stored for anonymous submissions - Proposal section 13."""
        if self.is_anonymous or self.student is None:
            return "Anonymous"
        return self.student.user.display_name


class CourseFeedback(models.Model):
    """Teaching-quality feedback: rated Always / Mostly / Seldom / Never."""

    RATING_CHOICES = [(3, "Always"), (2, "Mostly"), (1, "Seldom"), (0, "Never")]

    QUESTIONS = [
        "The teacher starts and finishes the class on time.",
        "The course outline was shared and followed.",
        "Concepts are explained clearly and with relevant examples.",
        "The teacher encourages questions and class participation.",
        "Assignments and class tests are returned with useful feedback.",
        "The teacher is available during the announced consultation hours.",
        "Assessment is fair and free from bias.",
        "The course improved my understanding of the subject.",
    ]

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="feedback")
    question_no = models.PositiveSmallIntegerField()
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=3)
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_no"]
        unique_together = ("enrollment", "question_no")
        verbose_name = "course feedback"
        verbose_name_plural = "course feedback"

    def __str__(self):
        return f"Q{self.question_no} - {self.get_rating_display()}"

    @property
    def question_text(self):
        idx = self.question_no - 1
        return self.QUESTIONS[idx] if 0 <= idx < len(self.QUESTIONS) else ""


class Award(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="awards")
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=60, default="Academic")
    awarded_by = models.CharField(max_length=120, blank=True)
    year = models.PositiveIntegerField(default=2026)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return self.title


# --------------------------------------------------------------------------
# Teacher self-service
# --------------------------------------------------------------------------
class RequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class LeaveApplication(models.Model):
    class LeaveType(models.TextChoices):
        CASUAL = "CASUAL", "Casual leave"
        EARNED = "EARNED", "Earned leave"
        MEDICAL = "MEDICAL", "Medical leave"
        STUDY = "STUDY", "Study leave"
        MATERNITY = "MATERNITY", "Maternity leave"

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices,
                                  default=LeaveType.CASUAL)
    from_date = models.DateField()
    to_date = models.DateField()
    reason = models.TextField()
    address_during_leave = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.PENDING)
    remarks = models.CharField(max_length=200, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.teacher.user.display_name} - {self.get_leave_type_display()}"

    @property
    def days(self):
        return (self.to_date - self.from_date).days + 1


class HouseAllotment(models.Model):
    class Category(models.TextChoices):
        A = "A", "Category A - Professor"
        B = "B", "Category B - Associate Professor"
        C = "C", "Category C - Assistant Professor"
        D = "D", "Category D - Lecturer / Officer"

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="house_requests")
    house_category = models.CharField(max_length=1, choices=Category.choices, default=Category.D)
    preferred_quarter = models.CharField(max_length=80, blank=True)
    family_members = models.PositiveSmallIntegerField(default=1)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]

    def __str__(self):
        return f"House request - {self.teacher.user.display_name}"


class VehicleRequisition(models.Model):
    class Vehicle(models.TextChoices):
        MICROBUS = "MICROBUS", "Microbus"
        CAR = "CAR", "Car"
        BUS = "BUS", "Bus"
        AMBULANCE = "AMBULANCE", "Ambulance"

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE,
                                related_name="vehicle_requests")
    vehicle_type = models.CharField(max_length=10, choices=Vehicle.choices,
                                    default=Vehicle.MICROBUS)
    purpose = models.CharField(max_length=200)
    destination = models.CharField(max_length=120)
    journey_date = models.DateField()
    return_date = models.DateField(blank=True, null=True)
    passengers = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-journey_date"]
        verbose_name = "vehicle requisition"

    def __str__(self):
        return f"{self.get_vehicle_type_display()} - {self.destination}"


class Event(models.Model):
    class Kind(models.TextChoices):
        SEMINAR = "SEMINAR", "Seminar"
        WORKSHOP = "WORKSHOP", "Workshop"
        MEETING = "MEETING", "Faculty meeting"
        CULTURAL = "CULTURAL", "Cultural programme"

    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SEMINAR)
    organizer = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="events")
    venue = models.CharField(max_length=120)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_at"]

    def __str__(self):
        return self.title


# --------------------------------------------------------------------------
# Research & development
# --------------------------------------------------------------------------
class ResearchPost(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="research_posts")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=60, default="Research news")
    body = models.TextField()
    published_at = models.DateField(default=timezone.now)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class Publication(models.Model):
    class Kind(models.TextChoices):
        JOURNAL = "JOURNAL", "Journal article"
        CONFERENCE = "CONFERENCE", "Conference paper"
        BOOK = "BOOK", "Book / chapter"

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="publications")
    title = models.CharField(max_length=250)
    authors = models.CharField(max_length=250, blank=True)
    journal_name = models.CharField(max_length=180, blank=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.JOURNAL)
    year = models.PositiveIntegerField(default=2026)
    indexing = models.CharField(max_length=60, blank=True, help_text="Scopus, SCIE, etc.")
    doi_link = models.URLField(blank=True)
    in_baures = models.BooleanField("listed in BAURES repository", default=False)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return self.title


class ExamRemuneration(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSED = "PROCESSED", "Processed"
        PAID = "PAID", "Paid"

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="remunerations")
    exam_title = models.CharField(max_length=120)
    particulars = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    bill_date = models.DateField(default=timezone.now)
    paid_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-bill_date"]
        verbose_name = "exam remuneration"

    def __str__(self):
        return f"{self.exam_title} - {self.amount} BDT"


class PostgraduateApplication(models.Model):
    """M.S. / MBA / PhD applications reviewed by supervisors (Proposal 7.2)."""

    class Program(models.TextChoices):
        MS = "MS", "M.S."
        MBA = "MBA", "MBA"
        PHD = "PHD", "PhD"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="pg_applications")
    supervisor = models.ForeignKey(Teacher, on_delete=models.CASCADE,
                                   related_name="pg_applications")
    program = models.CharField(max_length=4, choices=Program.choices, default=Program.MS)
    research_title = models.CharField(max_length=220)
    synopsis = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=RequestStatus.choices,
                              default=RequestStatus.PENDING)
    thesis_marks = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "postgraduate application"

    def __str__(self):
        return f"{self.get_program_display()} - {self.research_title[:40]}"
