"""
Academic core - a direct implementation of Figure 2 (Core Database ERD) in the
JSTU ERP proposal: Department, Program, Student, Teacher, Course, CourseOffer,
Enrollment, Marks, ExamRoutine, AdmitCard, FormFillup and FeePayment.
"""

import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone

# Year of study, spelt the way the university writes it: 1st Year ... 4th Year.
YEAR_SUFFIX = {1: "st", 2: "nd", 3: "rd", 4: "th"}
YEAR_CHOICES = [(n, f"{n}{YEAR_SUFFIX.get(n, 'th')} Year") for n in range(1, 5)]

# What may be attached to a notice: a PDF or a picture of the memo.
NOTICE_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "webp"]
NOTICE_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")

# Proof of payment a student uploads: a phone photo of the bank slip, a scan,
# or the PDF an online transfer produces.
RECEIPT_EXTENSIONS = ["pdf", "png", "jpg", "jpeg", "webp"]
RECEIPT_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
RECEIPT_MAX_BYTES = 5 * 1024 * 1024


# --------------------------------------------------------------------------
# Organisation
# --------------------------------------------------------------------------
class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=10, unique=True)
    faculty_name = models.CharField(max_length=120)
    established_year = models.PositiveIntegerField(default=2018)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Program(models.Model):
    class Level(models.TextChoices):
        BACHELOR = "BSC", "Bachelor"
        MASTERS = "MS", "M.S. / MBA"
        PHD = "PHD", "PhD"

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    degree_level = models.CharField(max_length=4, choices=Level.choices, default=Level.BACHELOR)
    duration_years = models.PositiveSmallIntegerField(default=4)

    class Meta:
        ordering = ["department__code", "name"]

    def __str__(self):
        return self.name

    @property
    def level_label(self):
        """How the degree level reads on an ID card."""
        return {
            self.Level.BACHELOR: "Undergraduate student",
            self.Level.MASTERS: "Postgraduate student",
            self.Level.PHD: "Doctoral researcher",
        }.get(self.degree_level, "Student")


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------
class Student(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRADUATED = "GRADUATED", "Graduated"
        DROPPED = "DROPPED", "Dropped out"
        SUSPENDED = "SUSPENDED", "Suspended"

    class Religion(models.TextChoices):
        ISLAM = "ISLAM", "Islam"
        HINDU = "HINDU", "Hindu"
        CHRISTIAN = "CHRISTIAN", "Christian"
        BUDDHIST = "BUDDHIST", "Buddhist"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="student")
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="students")
    student_id = models.CharField(max_length=20, unique=True)
    registration_no = models.CharField(max_length=25, unique=True)
    session = models.CharField(max_length=12, help_text="e.g. 2024-25")
    level = models.PositiveSmallIntegerField(default=1)
    semester = models.PositiveSmallIntegerField(default=1)
    batch_year = models.PositiveIntegerField(default=2024)
    # Personal
    # The English name lives on the user account; this is the Bangla spelling
    # the university prints on certificates and official lists.
    name_bn = models.CharField("name (Bangla)", max_length=120, blank=True)
    father_name = models.CharField("father's name", max_length=120, blank=True)
    father_name_bn = models.CharField("father's name (Bangla)", max_length=120, blank=True)
    mother_name = models.CharField("mother's name", max_length=120, blank=True)
    mother_name_bn = models.CharField("mother's name (Bangla)", max_length=120, blank=True)
    religion = models.CharField(max_length=10, choices=Religion.choices, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    contact_no = models.CharField(max_length=20, blank=True)
    present_address = models.CharField(max_length=200, blank=True)
    permanent_address = models.CharField(max_length=200, blank=True)
    photo_url = models.URLField(blank=True)
    # Uploaded once, then reused on every examination form.
    signature = models.ImageField(upload_to="signatures/", blank=True, null=True,
                                  help_text="Scanned signature used on exam forms.")
    # Guardian
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_relation = models.CharField(max_length=40, blank=True)
    guardian_contact = models.CharField(max_length=20, blank=True)
    guardian_occupation = models.CharField(max_length=80, blank=True)
    # Bank (scholarship / stipend disbursement)
    bank_name = models.CharField(max_length=80, blank=True)
    bank_branch = models.CharField(max_length=80, blank=True)
    bank_account_no = models.CharField(max_length=30, blank=True)
    # Campus services
    university_email = models.EmailField(blank=True)
    internet_username = models.CharField(max_length=40, blank=True)
    internet_active = models.BooleanField(default=True)
    data_quota_gb = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        ordering = ["student_id"]

    def __str__(self):
        return f"{self.student_id} - {self.user.display_name}"

    @property
    def department(self):
        return self.program.department

    def _guardian_if(self, *relations):
        """The guardian's name when the recorded relation matches."""
        if self.guardian_relation.strip().lower() in relations:
            return self.guardian_name
        return ""

    @property
    def father_display(self):
        """Father's name, falling back to the guardian when he is the guardian."""
        return self.father_name or self._guardian_if("father", "পিতা", "baba")

    @property
    def mother_display(self):
        return self.mother_name or self._guardian_if("mother", "মাতা", "ma")

    @property
    def missing_form_details(self):
        """Labels of the personal details an examination form still needs."""
        required = [
            (self.name_bn, "name in Bangla"),
            (self.father_display, "father's name"),
            (self.mother_display, "mother's name"),
            (self.religion, "religion"),
            (self.present_address, "present address"),
            (self.permanent_address, "permanent address"),
            (self.contact_no, "mobile number"),
        ]
        return [label for value, label in required if not value]

    # Every detail the student can fill in themselves, with the Student Panel
    # page that edits it. The registrar-maintained fields (ID, programme,
    # session, university e-mail...) are deliberately left out: the meter only
    # counts gaps the student can actually close.
    PROFILE_FIELDS = [
        ("name_bn", "Name (Bangla)", "guardian"),
        ("father_name", "Father's name", "guardian"),
        ("mother_name", "Mother's name", "guardian"),
        ("religion", "Religion", "guardian"),
        ("blood_group", "Blood group", "guardian"),
        ("contact_no", "Contact number", "guardian"),
        ("present_address", "Present address", "guardian"),
        ("permanent_address", "Permanent address", "guardian"),
        ("guardian_name", "Guardian's name", "guardian"),
        ("guardian_relation", "Guardian's relation", "guardian"),
        ("guardian_contact", "Guardian's contact", "guardian"),
        ("guardian_occupation", "Guardian's occupation", "guardian"),
        ("bank_name", "Bank name", "bank"),
        ("bank_branch", "Bank branch", "bank"),
        ("bank_account_no", "Bank account no.", "bank"),
    ]

    @property
    def profile_gaps(self):
        """The details above that are still blank, and where to fill each in."""
        return [{"label": label, "page": page}
                for field, label, page in self.PROFILE_FIELDS
                if not getattr(self, field)]

    @property
    def profile_completeness(self):
        """How much of that record is on file, as a percentage 0-100.

        Drives the completeness meter on the student's profile page.
        """
        total = len(self.PROFILE_FIELDS)
        return round(100 * (total - len(self.profile_gaps)) / total)

    @property
    def cgpa(self):
        rows = Marks.objects.filter(enrollment__student=self, is_published=True,
                                    gpa__isnull=False)
        credits = total = 0.0
        for row in rows:
            credit = float(row.enrollment.offer.course.credit)
            credits += credit
            total += credit * float(row.gpa)
        return round(total / credits, 2) if credits else 0.00


class Teacher(models.Model):
    class Designation(models.TextChoices):
        LECTURER = "LECTURER", "Lecturer"
        ASSISTANT = "ASSISTANT", "Assistant Professor"
        ASSOCIATE = "ASSOCIATE", "Associate Professor"
        PROFESSOR = "PROFESSOR", "Professor"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="teacher")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="teachers")
    employee_id = models.CharField(max_length=20, unique=True)
    designation = models.CharField(max_length=12, choices=Designation.choices,
                                   default=Designation.LECTURER)
    joining_date = models.DateField(default=timezone.now)
    contact_no = models.CharField(max_length=20, blank=True)
    office_room = models.CharField(max_length=60, blank=True)
    specialization = models.CharField(max_length=160, blank=True)
    photo_url = models.URLField(blank=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self):
        return f"{self.user.display_name} ({self.get_designation_display()})"


# --------------------------------------------------------------------------
# Curriculum
# --------------------------------------------------------------------------
class Course(models.Model):
    class Category(models.TextChoices):
        COMPULSORY = "COMPULSORY", "Compulsory"
        OPTIONAL = "OPTIONAL", "Optional"
        ELECTIVE = "ELECTIVE", "Elective"

    class Type(models.TextChoices):
        THEORY = "THEORY", "Theory"
        PRACTICAL = "PRACTICAL", "Practical / Lab"
        THESIS = "THESIS", "Thesis / Project"

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    course_code = models.CharField(max_length=12, unique=True)
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=12, choices=Category.choices,
                                default=Category.COMPULSORY)
    course_type = models.CharField(max_length=10, choices=Type.choices, default=Type.THEORY)
    credit = models.DecimalField(max_digits=3, decimal_places=1, default=3.0)
    contact_hour = models.PositiveSmallIntegerField(default=3)
    year = models.PositiveSmallIntegerField(default=1)
    semester = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["course_code"]

    def __str__(self):
        return f"{self.course_code} - {self.title}"


class CourseOffer(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="offers")
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="offers")
    level = models.CharField(max_length=4, choices=Program.Level.choices,
                             default=Program.Level.BACHELOR,
                             help_text="Degree level - Bachelor, M.S. or PhD.")
    year = models.PositiveSmallIntegerField(default=1,
                                            help_text="Year of study - 1st to 4th.")
    semester = models.PositiveSmallIntegerField(default=1)
    calendar_year = models.PositiveIntegerField(default=2026,
                                                help_text="The running calendar year, e.g. 2026.")
    seat_capacity = models.PositiveSmallIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-calendar_year", "level", "year", "semester", "course__course_code"]
        unique_together = ("course", "level", "year", "semester", "calendar_year")

    def __str__(self):
        return (f"{self.course.course_code} ({self.calendar_year} "
                f"{self.get_level_display()} Y{self.year}T{self.semester})")

    @property
    def year_label(self):
        """1 -> '1st Year', 2 -> '2nd Year', ..."""
        return f"{self.year}{YEAR_SUFFIX.get(self.year, 'th')} Year"

    @property
    def enrolled_count(self):
        return self.enrollments.filter(status=Enrollment.Status.ENROLLED).count()

    @property
    def seats_left(self):
        return max(self.seat_capacity - self.enrolled_count, 0)


class EnrollmentDeadline(models.Model):
    exam_title = models.CharField(max_length=120, help_text="e.g. Semester Final, Spring 2026")
    level = models.CharField(max_length=4, choices=Program.Level.choices,
                             default=Program.Level.BACHELOR,
                             help_text="Degree level - Bachelor, M.S. or PhD.")
    year = models.PositiveSmallIntegerField(default=1,
                                            help_text="Year of study - 1st to 4th.")
    semester = models.PositiveSmallIntegerField(default=1)
    calendar_year = models.PositiveIntegerField(default=2026,
                                                help_text="The running calendar year, e.g. 2026.")
    start_date = models.DateField()
    end_date = models.DateField()
    late_end_date = models.DateField(blank=True, null=True)
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=3500)
    late_fee_amount = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    is_open = models.BooleanField(default=True)
    # Both optional - a window may carry a written notice, an attachment,
    # either, or neither.
    notice = models.TextField(blank=True,
                              help_text="Optional notice shown to students.")
    notice_file = models.FileField(
        upload_to="notices/", blank=True, null=True,
        validators=[FileExtensionValidator(NOTICE_EXTENSIONS)],
        help_text="Optional PDF or image attachment.")

    class Meta:
        ordering = ["-calendar_year", "level", "year", "semester"]
        verbose_name = "enrollment deadline"

    def __str__(self):
        return f"{self.exam_title} - {self.get_level_display()} Y{self.year}/T{self.semester}"

    @property
    def year_label(self):
        """1 -> '1st Year', 2 -> '2nd Year', ..."""
        return f"{self.year}{YEAR_SUFFIX.get(self.year, 'th')} Year"

    @property
    def notice_is_image(self):
        """True when the attachment can be shown inline rather than linked."""
        if not self.notice_file:
            return False
        return self.notice_file.name.lower().endswith(NOTICE_IMAGE_SUFFIXES)

    @property
    def notice_filename(self):
        return os.path.basename(self.notice_file.name) if self.notice_file else ""

    @property
    def window_state(self):
        today = timezone.localdate()
        if not self.is_open:
            return "Closed"
        if today < self.start_date:
            return "Upcoming"
        if today <= self.end_date:
            return "Open"
        if self.late_end_date and today <= self.late_end_date:
            return "Late window"
        return "Expired"

    @property
    def is_applicable(self):
        """True while a student may still start or change a form for this window.

        The late period counts: an application is accepted right up to
        `late_end_date`. Once that passes there is no self-service route left.
        """
        return self.window_state in ("Open", "Late window")

    @property
    def closing_date(self):
        """The last day an application is accepted, late period included."""
        return self.late_end_date or self.end_date

    @property
    def closed_notice(self):
        """Why this window cannot be applied to, and who to take it to."""
        state = self.window_state
        if state == "Upcoming":
            return (f"The form fill-up window for {self.exam_title} opens on "
                    f"{self.start_date:%d %b %Y}.")
        if state == "Closed":
            return (f"The form fill-up window for {self.exam_title} has been closed "
                    f"by the Examination Controller. Contact the Chairman of your "
                    f"department if you still need to apply.")
        return (f"The form fill-up window for {self.exam_title} expired on "
                f"{self.closing_date:%d %b %Y}, including the late period. "
                f"Contact the Chairman of your department to apply after the deadline.")


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = "ENROLLED", "Enrolled"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    offer = models.ForeignKey(CourseOffer, on_delete=models.CASCADE, related_name="enrollments")
    enrollment_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ENROLLED)

    class Meta:
        ordering = ["-enrollment_date"]
        unique_together = ("student", "offer")

    def __str__(self):
        return f"{self.student.student_id} -> {self.offer.course.course_code}"


class Marks(models.Model):
    """Attendance / class-test / final marks against one enrollment."""

    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="marks")
    attendance_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ct_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    repeat_final_marks = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    grade = models.CharField(max_length=3, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "marks"

    def __str__(self):
        return f"Marks - {self.enrollment}"

    @property
    def total(self):
        final = self.repeat_final_marks if self.repeat_final_marks is not None else self.final_marks
        return round(float(self.attendance_marks) + float(self.ct_marks) + float(final), 2)

    def compute_grade(self):
        """Standard 4.00-scale grading used by JSTU."""
        total = self.total
        table = [
            (80, "A+", 4.00), (75, "A", 3.75), (70, "A-", 3.50), (65, "B+", 3.25),
            (60, "B", 3.00), (55, "B-", 2.75), (50, "C+", 2.50), (45, "C", 2.25),
            (40, "D", 2.00),
        ]
        for cutoff, letter, point in table:
            if total >= cutoff:
                return letter, point
        return "F", 0.00

    def save(self, *args, **kwargs):
        self.grade, gpa = self.compute_grade()
        self.gpa = gpa
        super().save(*args, **kwargs)


# --------------------------------------------------------------------------
# Examination
# --------------------------------------------------------------------------
class ExamRoutine(models.Model):
    class ExamType(models.TextChoices):
        THEORY = "THEORY", "Theory"
        PRACTICAL = "PRACTICAL", "Practical"

    offer = models.ForeignKey(CourseOffer, on_delete=models.CASCADE, related_name="routines")
    exam_title = models.CharField(max_length=120, default="Semester Final")
    exam_type = models.CharField(max_length=10, choices=ExamType.choices,
                                 default=ExamType.THEORY)
    exam_date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=180)
    exam_place = models.CharField(max_length=120)
    memo_no = models.CharField(max_length=40, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["exam_date", "start_time"]

    def __str__(self):
        return f"{self.offer.course.course_code} - {self.exam_date}"


class ClassRoutine(models.Model):
    class Day(models.TextChoices):
        SUN = "SUN", "Sunday"
        MON = "MON", "Monday"
        TUE = "TUE", "Tuesday"
        WED = "WED", "Wednesday"
        THU = "THU", "Thursday"

    offer = models.ForeignKey(CourseOffer, on_delete=models.CASCADE, related_name="classes")
    day = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=40)

    class Meta:
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.offer.course.course_code} - {self.get_day_display()} {self.start_time}"


class FormFillup(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"

    class ExamineeType(models.TextChoices):
        REGULAR = "REGULAR", "নিয়মিত"
        IRREGULAR = "IRREGULAR", "অনিয়মিত"
        IMPROVEMENT = "IMPROVEMENT", "মান উন্নয়ন"

    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending semester"
        ACCOUNTS = "ACCOUNTS", "Accounts seen pending"
        APPROVED = "APPROVED", "Approved semester"
        FINAL = "FINAL", "Final approval"
        HELD = "HELD", "Held"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="form_fillups")
    deadline = models.ForeignKey(EnrollmentDeadline, on_delete=models.PROTECT,
                                 related_name="form_fillups")
    invoice_no = models.CharField(max_length=24, unique=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=3500)
    payment_status = models.CharField(max_length=8, choices=PaymentStatus.choices,
                                      default=PaymentStatus.UNPAID)
    approval_status = models.CharField(max_length=10, choices=ApprovalStatus.choices,
                                       default=ApprovalStatus.PENDING)
    is_late = models.BooleanField(default=False)
    applied_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(blank=True, null=True)
    remarks = models.CharField(max_length=200, blank=True)
    # Courses the student listed on the examination form.
    courses = models.ManyToManyField(CourseOffer, blank=True,
                                     related_name="form_fillups")
    examinee_type = models.CharField(max_length=12, choices=ExamineeType.choices,
                                     blank=True,
                                     help_text="Ticked on the examination form.")
    signed = models.BooleanField(default=False,
                                 help_text="Student attached their signature.")
    is_submitted = models.BooleanField(default=False,
                                       help_text="Marked done; awaiting payment.")

    class Meta:
        ordering = ["-applied_at"]
        unique_together = ("student", "deadline")
        verbose_name = "form fill-up"

    def __str__(self):
        return f"{self.invoice_no} - {self.student.student_id}"

    @property
    def is_approved(self):
        """True once the application has cleared approval."""
        return self.approval_status in (self.ApprovalStatus.APPROVED,
                                        self.ApprovalStatus.FINAL)

    def ensure_admit_card(self):
        """Raise the admit card for an approved application.

        Called wherever approval is granted, so the card exists the moment the
        Registrar approves rather than only after a separate bulk run. The
        serial is derived from the window and the student, both of which are
        already unique together, so re-running this never mints a duplicate.
        Returns (card, created); (None, False) while still unapproved.
        """
        if not self.is_approved:
            return None, False
        return AdmitCard.objects.get_or_create(
            student=self.student, deadline=self.deadline,
            defaults={"serial_no": f"AC-{self.deadline.pk}-{self.student.student_id}"},
        )

    @property
    def state_tone(self):
        return {
            self.ApprovalStatus.FINAL: "emerald",
            self.ApprovalStatus.APPROVED: "emerald",
            self.ApprovalStatus.ACCOUNTS: "amber",
            self.ApprovalStatus.PENDING: "sky",
            self.ApprovalStatus.HELD: "amber",
            self.ApprovalStatus.REJECTED: "rose",
        }.get(self.approval_status, "slate")


class FeePayment(models.Model):
    class Method(models.TextChoices):
        JANATA = "JANATA", "Janata Bank Gateway"
        BKASH = "BKASH", "bKash"
        NAGAD = "NAGAD", "Nagad"
        COUNTER = "COUNTER", "Bank counter"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        FAILED = "FAILED", "Failed"

    form_fillup = models.ForeignKey(FormFillup, on_delete=models.CASCADE, related_name="payments")
    invoice_no = models.CharField(max_length=24)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=8, choices=Method.choices, default=Method.JANATA)
    transaction_id = models.CharField(max_length=40, blank=True)
    payment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    # Proof the student paid at the counter. The Accounts Office opens this,
    # checks it against the invoice, and marks the payment verified.
    receipt = models.FileField(
        upload_to="receipts/", blank=True, null=True,
        validators=[FileExtensionValidator(RECEIPT_EXTENSIONS)],
        help_text="Bank payment slip uploaded by the student.")
    remarks = models.CharField(max_length=200, blank=True,
                               help_text="Why the Accounts Office rejected the slip.")
    verified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.invoice_no} - {self.amount} BDT"

    @property
    def receipt_is_image(self):
        """True when the slip can be previewed inline rather than linked."""
        if not self.receipt:
            return False
        return self.receipt.name.lower().endswith(RECEIPT_IMAGE_SUFFIXES)

    @property
    def receipt_filename(self):
        return os.path.basename(self.receipt.name) if self.receipt else ""


class AdmitCard(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="admit_cards")
    deadline = models.ForeignKey(EnrollmentDeadline, on_delete=models.CASCADE,
                                 related_name="admit_cards")
    serial_no = models.CharField(max_length=24, unique=True)
    issue_date = models.DateField(default=timezone.now)
    signed_by = models.CharField(max_length=120, default="Controller of Examinations, JSTU")
    is_released = models.BooleanField(default=False)

    class Meta:
        ordering = ["-issue_date"]
        unique_together = ("student", "deadline")

    def __str__(self):
        return f"{self.serial_no} - {self.student.student_id}"

    @property
    def courses(self):
        return Enrollment.objects.filter(
            student=self.student,
            offer__level=self.deadline.level,
            offer__year=self.deadline.year,
            offer__semester=self.deadline.semester,
            offer__calendar_year=self.deadline.calendar_year,
            status=Enrollment.Status.ENROLLED,
        ).select_related("offer__course")
