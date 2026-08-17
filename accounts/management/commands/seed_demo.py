"""
Populate the ERP with a realistic JSTU dataset so every panel has something to
show on the first run, and issue the entry passkeys for the demo accounts.

    python manage.py seed_demo
"""

import random
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from academics.models import (AdmitCard, ClassRoutine, Course, CourseOffer,
                              Department, Enrollment, EnrollmentDeadline,
                              ExamRoutine, FeePayment, FormFillup, Marks,
                              Program, Student, Teacher)
from accounts.models import AccessPasskey, Designation, Role, User
from portal.models import (Award, ComplaintSuggestion, CourseFeedback, Event,
                           ExamRemuneration, HouseAllotment, LeaveApplication,
                           Notice, PostgraduateApplication, Publication,
                           RequestStatus, ResearchPost, VehicleRequisition,
                           WebsiteMenu)

FIRST = ["Rahim", "Karim", "Sadia", "Nusrat", "Tanvir", "Mahmud", "Farhana", "Imran",
         "Shakil", "Rumana", "Arif", "Sabbir", "Mitu", "Jahid", "Sumaiya", "Rakib",
         "Tasnim", "Naimul", "Sharmin", "Fahim", "Ruma", "Anik", "Priya", "Rased"]
LAST = ["Uddin", "Hasan", "Akter", "Rahman", "Islam", "Chowdhury", "Sarker", "Hossain",
        "Ahmed", "Khatun", "Mia", "Bhuiyan"]


class Command(BaseCommand):
    help = "Load a demo dataset for the JSTU ERP and issue entry passkeys."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=40,
                            help="How many student accounts to create (default 40).")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)
        year = timezone.now().year
        self.stdout.write("Seeding the JSTU ERP...")

        # ---------------------------------------------------------------- org
        depts = {}
        for code, name, faculty in [
            ("CSE", "Computer Science and Engineering", "Faculty of Engineering"),
            ("EEE", "Electrical and Electronic Engineering", "Faculty of Engineering"),
            ("BBA", "Business Administration", "Faculty of Business Studies"),
            ("MAT", "Mathematics", "Faculty of Science"),
        ]:
            depts[code], _ = Department.objects.get_or_create(
                code=code, defaults={"name": name, "faculty_name": faculty,
                                     "established_year": 2018})

        programs = {}
        for code, name, dept in [
            ("BSC-CSE", "B.Sc. in Computer Science and Engineering", "CSE"),
            ("BSC-EEE", "B.Sc. in Electrical and Electronic Engineering", "EEE"),
            ("BBA-GEN", "Bachelor of Business Administration", "BBA"),
        ]:
            programs[code], _ = Program.objects.get_or_create(
                code=code, defaults={"name": name, "department": depts[dept],
                                     "duration_years": 4})

        # ------------------------------------------------------------- courses
        catalogue = [
            ("CSE 3102", "Data Structures", "CSE", 3.0, 3, 1),
            ("CSE 4105", "Database Systems", "CSE", 3.0, 4, 2),
            ("CSE 4109", "Software Engineering", "CSE", 3.0, 4, 2),
            ("CSE 5103", "Compiler Design", "CSE", 3.0, 3, 2),
            ("CSE 3104", "Algorithms Laboratory", "CSE", 1.5, 3, 1),
            ("CSE 3106", "Operating Systems", "CSE", 3.0, 3, 2),
            ("EEE 2101", "Electrical Circuits", "EEE", 3.0, 2, 1),
            ("EEE 3201", "Digital Electronics", "EEE", 3.0, 3, 1),
            ("MAT 1101", "Differential Calculus", "MAT", 3.0, 1, 1),
            ("BBA 2103", "Principles of Marketing", "BBA", 3.0, 2, 1),
        ]
        courses = {}
        for code, title, dept, credit, level, sem in catalogue:
            kind = Course.Type.PRACTICAL if "Laborator" in title else Course.Type.THEORY
            courses[code], _ = Course.objects.get_or_create(
                course_code=code,
                defaults={"title": title, "department": depts[dept], "credit": credit,
                          "contact_hour": int(credit * 1.5) or 2, "year": level,
                          "semester": sem, "course_type": kind,
                          "category": Course.Category.COMPULSORY})

        # ------------------------------------------------------------ teachers
        faculty_spec = [
            ("Mohammad", "Hasan", "CSE", Teacher.Designation.ASSISTANT,
             "Bioinformatics, deep learning on biomedical data"),
            ("Nazia", "Sultana", "CSE", Teacher.Designation.LECTURER, "Databases, data mining"),
            ("Rezaul", "Karim", "EEE", Teacher.Designation.ASSOCIATE, "Power systems"),
            ("Afsana", "Mimi", "BBA", Teacher.Designation.LECTURER, "Marketing strategy"),
        ]
        teachers = []
        for i, (first, last, dept, desig, spec) in enumerate(faculty_spec, start=1):
            user = self._user(f"{first.lower()}.{last.lower()}@jstu.edu.bd", first, last,
                              Role.TEACHER)
            teacher, _ = Teacher.objects.get_or_create(
                user=user,
                defaults={"department": depts[dept], "employee_id": f"T-2021-{i:03d}",
                          "designation": desig, "joining_date": date(2021, 8, 12),
                          "contact_no": f"0171234{i:04d}",
                          "office_room": f"{dept} Building, Room 3{i:02d}",
                          "specialization": spec})
            teachers.append(teacher)

        # --------------------------------------------------------------- admin
        admins = [
            ("Registrar", "Office", "registrar@jstu.edu.bd", Designation.REGISTRAR),
            ("Exam", "Controller", "exam@jstu.edu.bd", Designation.EXAM_CONTROLLER),
            ("Accounts", "Officer", "accounts@jstu.edu.bd", Designation.ACCOUNTS),
            ("ICT", "Cell", "ict@jstu.edu.bd", Designation.ICT),
        ]
        for first, last, mail, desig in admins:
            self._user(mail, first, last, Role.ADMIN, designation=desig)

        # ------------------------------------------------------------- offers
        offers = []
        for code in ["CSE 3102", "CSE 4105", "CSE 4109", "CSE 5103", "CSE 3104",
                     "CSE 3106", "EEE 2101", "EEE 3201", "MAT 1101", "BBA 2103"]:
            course = courses[code]
            teacher = teachers[0] if code.startswith("CSE") and code in (
                "CSE 3102", "CSE 4105", "CSE 4109", "CSE 5103") else random.choice(teachers)
            offer, _ = CourseOffer.objects.get_or_create(
                course=course, year=course.year, semester=course.semester,
                calendar_year=year,
                defaults={"teacher": teacher, "seat_capacity": 60})
            offers.append(offer)

        # -------------------------------------------------------------- routine
        slots = [("SUN", 9), ("MON", 11), ("TUE", 9), ("WED", 14), ("THU", 11)]
        for idx, offer in enumerate(offers):
            day, hour = slots[idx % len(slots)]
            ClassRoutine.objects.get_or_create(
                offer=offer, day=day, start_time=time(hour, 0),
                defaults={"end_time": time(hour + 1, 0),
                          "room": f"{offer.course.department.code} {300 + idx}"})

        # ------------------------------------------------------------- students
        created = []
        for i in range(1, options["students"] + 1):
            first, last = random.choice(FIRST), random.choice(LAST)
            program = programs["BSC-CSE"] if i % 3 else random.choice(list(programs.values()))
            user = self._user(f"student{i:03d}@jstu.edu.bd", first, last, Role.STUDENT)
            student, made = Student.objects.get_or_create(
                user=user,
                defaults={
                    "program": program, "student_id": f"2021-15-{1000 + i}",
                    "registration_no": f"JSTU-{year - 2}-{20000 + i}",
                    "session": "2024-25", "level": 3, "semester": 2, "batch_year": 2021,
                    "date_of_birth": date(2003, ((i - 1) % 12) + 1, ((i * 3) % 27) + 1),
                    "gender": "Male" if i % 2 else "Female",
                    "blood_group": random.choice(["A+", "B+", "O+", "AB+", "O-"]),
                    "contact_no": f"01712{300000 + i}",
                    "present_address": "Jamalpur, Bangladesh",
                    "permanent_address": random.choice(
                        ["Jamalpur", "Mymensingh", "Tangail", "Sherpur", "Dhaka"]) + ", Bangladesh",
                    "guardian_name": f"{random.choice(FIRST)} {last}",
                    "guardian_relation": "Father", "guardian_contact": f"01812{400000 + i}",
                    "guardian_occupation": random.choice(["Teacher", "Farmer", "Business", "Service"]),
                    "bank_name": "Janata Bank PLC", "bank_branch": "Jamalpur Branch",
                    "bank_account_no": f"01001{random.randint(10**8, 10**9 - 1)}",
                    "university_email": f"student{i:03d}@jstu.edu.bd",
                    "internet_username": f"2021151{i:03d}",
                })
            created.append(student)

        # ----------------------------------------------------------- enrollment
        cse_offers = [o for o in offers if o.course.course_code.startswith("CSE")][:4]
        for student in created:
            for offer in cse_offers:
                enrollment, _ = Enrollment.objects.get_or_create(
                    student=student, offer=offer,
                    defaults={"enrollment_date": timezone.localdate() - timedelta(days=40)})
                row, made = Marks.objects.get_or_create(
                    enrollment=enrollment,
                    defaults={"attendance_marks": random.randint(6, 10),
                              "ct_marks": random.randint(10, 20),
                              "final_marks": random.randint(35, 68),
                              "is_published": random.random() > 0.35})
                if made:
                    row.save()

        # ------------------------------------------------------------- deadline
        today = timezone.localdate()
        deadline, _ = EnrollmentDeadline.objects.get_or_create(
            exam_title=f"Semester Final, Spring {year}", year=3, semester=2,
            calendar_year=year,
            defaults={"start_date": today - timedelta(days=10),
                      "end_date": today + timedelta(days=12),
                      "late_end_date": today + timedelta(days=20),
                      "fee_amount": 3500, "late_fee_amount": 500,
                      "notice": f"Memo no. JSTU/EXAM/{year}/014. Clear all dues "
                                f"before applying; late fill-up carries a BDT 500 fee."})

        S = FormFillup.ApprovalStatus
        states = [S.PENDING, S.ACCOUNTS, S.APPROVED, S.FINAL, S.HELD]
        for i, student in enumerate(created):
            state = states[i % len(states)]
            paid = state in (S.ACCOUNTS, S.APPROVED, S.FINAL)
            fillup, made = FormFillup.objects.get_or_create(
                student=student, deadline=deadline,
                defaults={"invoice_no": f"JSTU-{year}{today:%m}-{50000 + i}",
                          "amount": 3500, "approval_status": state,
                          "payment_status": FormFillup.PaymentStatus.PAID if paid
                          else FormFillup.PaymentStatus.UNPAID})
            if made and paid:
                FeePayment.objects.create(
                    form_fillup=fillup, invoice_no=fillup.invoice_no, amount=fillup.amount,
                    method=FeePayment.Method.JANATA,
                    transaction_id=f"TXN{random.randint(10**9, 10**10 - 1)}",
                    status=FeePayment.Status.VERIFIED)
            if state == S.FINAL:
                AdmitCard.objects.get_or_create(
                    student=student, deadline=deadline,
                    defaults={"serial_no": f"AC-{year}-{700000 + i}", "is_released": True})

        # ------------------------------------------------------------ exam plan
        for idx, offer in enumerate(cse_offers):
            ExamRoutine.objects.get_or_create(
                offer=offer, exam_title=deadline.exam_title,
                exam_date=today + timedelta(days=30 + idx * 3),
                defaults={"start_time": time(10, 0), "duration_minutes": 180,
                          "exam_place": f"Exam Hall {idx + 1}, Academic Building 1",
                          "memo_no": f"JSTU/EXAM/{year}/0{31 + idx}",
                          "is_published": True})

        # -------------------------------------------------------------- notices
        for title, cat, aud in [
            (f"Final Exam Routine (Spring {year}) Published", Notice.Category.EXAM, Notice.Audience.ALL),
            (f"Form Fill-up for Summer {year} is now open", Notice.Category.EXAM, Notice.Audience.STUDENT),
            ("Scholarship Application Deadline Extended", Notice.Category.UNIVERSITY, Notice.Audience.STUDENT),
            ("Workshop on AI and Machine Learning", Notice.Category.EVENT, Notice.Audience.ALL),
            ("Department Meeting on the 18th", Notice.Category.DEPARTMENT, Notice.Audience.TEACHER),
            ("Teacher Feedback Analysis Report", Notice.Category.UNIVERSITY, Notice.Audience.TEACHER),
        ]:
            Notice.objects.get_or_create(
                title=title,
                defaults={"category": cat, "audience": aud,
                          "body": "Details are available at the Registrar's Office and on the "
                                  "university website. Students and faculty are requested to "
                                  "follow the published schedule.",
                          "post_date": today - timedelta(days=random.randint(1, 15))})

        for i, (title, order) in enumerate([("Home", 1), ("Admissions", 2), ("Academics", 3),
                                            ("Notice Board", 4), ("Contact", 5)]):
            WebsiteMenu.objects.get_or_create(page_title=title, defaults={"menu_order": order})

        # ----------------------------------------------------------- engagement
        for i, student in enumerate(created[:6]):
            ComplaintSuggestion.objects.get_or_create(
                tracking_code=f"JC-{600000 + i}",
                defaults={"student": None if i % 3 == 0 else student,
                          "is_anonymous": i % 3 == 0,
                          "kind": ComplaintSuggestion.Kind.COMPLAINT if i % 2
                          else ComplaintSuggestion.Kind.SUGGESTION,
                          "report_to": random.choice(
                              [c[0] for c in ComplaintSuggestion.Office.choices]),
                          "subject": random.choice([
                              "Library opening hours during examinations",
                              "Laboratory equipment needs maintenance",
                              "Request for extra shuttle bus in the morning",
                              "Classroom projector is not working",
                              "Water filter needed on the third floor",
                              "Wi-Fi coverage is weak in the reading room"]),
                          "message": "Raising this through the ERP complaint box so the office "
                                     "can look into it and record what action was taken."})

        for i, student in enumerate(created[:8]):
            Award.objects.get_or_create(
                student=student, title=random.choice([
                    "Dean's List Award", "Best Project Presentation",
                    "Inter-university Programming Contest Runner-up",
                    "Merit Scholarship"]),
                defaults={"category": "Academic", "year": year - (i % 2),
                          "awarded_by": "Jamalpur Science and Technology University",
                          "description": "Awarded in recognition of outstanding academic "
                                         "performance during the session."})

        for enrollment in Enrollment.objects.filter(offer__in=cse_offers)[:60]:
            for q in range(1, 9):
                CourseFeedback.objects.get_or_create(
                    enrollment=enrollment, question_no=q,
                    defaults={"rating": random.choice([3, 3, 2, 2, 1])})

        # ------------------------------------------------- teacher self-service
        for i, teacher in enumerate(teachers):
            LeaveApplication.objects.get_or_create(
                teacher=teacher, from_date=today + timedelta(days=5 + i),
                defaults={"to_date": today + timedelta(days=7 + i),
                          "leave_type": LeaveApplication.LeaveType.CASUAL,
                          "reason": "Personal work outside the district.",
                          "status": RequestStatus.PENDING if i < 2 else RequestStatus.APPROVED})
            HouseAllotment.objects.get_or_create(
                teacher=teacher,
                defaults={"house_category": HouseAllotment.Category.C,
                          "preferred_quarter": f"Block {chr(65 + i)}, Flat {i + 1}A",
                          "family_members": 3, "reason": "Currently living off campus."})
            VehicleRequisition.objects.get_or_create(
                teacher=teacher, journey_date=today + timedelta(days=9 + i),
                defaults={"vehicle_type": VehicleRequisition.Vehicle.MICROBUS,
                          "purpose": "Academic field visit with students.",
                          "destination": random.choice(["Dhaka", "Mymensingh", "Bogura"]),
                          "passengers": 12})
            Publication.objects.get_or_create(
                teacher=teacher,
                title=f"A study on {teacher.specialization.split(',')[0].lower()} "
                      f"for university-scale systems",
                defaults={"authors": teacher.user.display_name,
                          "journal_name": "Journal of Applied Computing",
                          "year": year - (i % 3), "indexing": "Scopus",
                          "in_baures": i % 2 == 0,
                          "doi_link": f"https://doi.org/10.1000/jstu.{year}.{100 + i}"})
            ExamRemuneration.objects.get_or_create(
                teacher=teacher, exam_title=deadline.exam_title,
                defaults={"particulars": "Script evaluation and invigilation",
                          "amount": 8500 + i * 500,
                          "status": ExamRemuneration.Status.PROCESSED if i % 2
                          else ExamRemuneration.Status.PAID,
                          "paid_date": today - timedelta(days=10) if i % 2 else None})
            ResearchPost.objects.get_or_create(
                teacher=teacher, title=f"Research update from the {teacher.department.code} lab",
                defaults={"category": "Research news",
                          "body": "A short summary of the current work, the datasets in use "
                                  "and what the team plans to publish next."})

        Event.objects.get_or_create(
            title="Workshop on AI and Machine Learning",
            defaults={"kind": Event.Kind.WORKSHOP, "organizer": teachers[0],
                      "venue": "CSE Seminar Room",
                      "start_at": timezone.now() + timedelta(days=7),
                      "end_at": timezone.now() + timedelta(days=7, hours=4),
                      "description": "Hands-on session for final-year students."})
        Event.objects.get_or_create(
            title="Faculty Meeting", defaults={
                "kind": Event.Kind.MEETING, "organizer": teachers[1],
                "venue": "Administrative Building, Conference Room",
                "start_at": timezone.now() + timedelta(days=3)})

        for i, student in enumerate(created[:3]):
            PostgraduateApplication.objects.get_or_create(
                student=student, supervisor=teachers[0],
                defaults={"program": PostgraduateApplication.Program.MS,
                          "research_title": "Deep learning for early disease detection "
                                            "from biomedical signals",
                          "synopsis": "The proposal outlines the dataset, the model family "
                                      "under consideration and the evaluation protocol."})

        # -------------------------------------------------------------- summary
        self.stdout.write(self.style.SUCCESS("\nDemo data loaded.\n"))
        self.stdout.write("Entry passkeys (e-mail + 6-digit code):\n")
        rows = [
            ("Student", "student001@jstu.edu.bd"),
            ("Teacher", "mohammad.hasan@jstu.edu.bd"),
            ("Registrar", "registrar@jstu.edu.bd"),
            ("Exam Controller", "exam@jstu.edu.bd"),
            ("Accounts", "accounts@jstu.edu.bd"),
            ("ICT Cell", "ict@jstu.edu.bd"),
        ]
        for label, mail in rows:
            user = User.objects.filter(email=mail).first()
            if user and hasattr(user, "passkey"):
                self.stdout.write(f"  {label:<16} {mail:<34} {user.passkey.code}")
        self.stdout.write(
            "\nEvery seeded account uses the same demo passkey. "
            "Issue fresh ones from the Django admin panel or from "
            "Admin Panel -> User & role management.\n")

    # ------------------------------------------------------------------ helper
    def _user(self, email, first, last, role, designation=""):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email.split("@")[0], "first_name": first,
                      "last_name": last, "role": role, "designation": designation})
        if created:
            user.set_password("jstu@2026")
            if role == Role.ADMIN:
                user.is_staff = True
                user.is_superuser = True
            user.save()
        AccessPasskey.objects.get_or_create(
            user=user, defaults={"code": "482913", "is_active": True,
                                 "note": "Demo passkey issued by seed_demo."})
        return user
