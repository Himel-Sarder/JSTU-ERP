from django.contrib import admin

from .models import (AdmitCard, ClassRoutine, Course, CourseOffer, Department,
                     Enrollment, EnrollmentDeadline, ExamRoutine, FeePayment,
                     FormFillup, Marks, Program, Student, Teacher)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty_name", "established_year")
    search_fields = ("name", "code")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "degree_level", "duration_years")
    list_filter = ("degree_level", "department")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "user", "program", "level", "semester", "session",
                    "religion", "status")
    list_filter = ("status", "level", "semester", "religion", "program__department")
    search_fields = ("student_id", "registration_no", "user__first_name", "user__email",
                     "name_bn", "father_name", "mother_name")
    raw_id_fields = ("user",)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "department", "designation", "joining_date")
    list_filter = ("designation", "department")
    search_fields = ("employee_id", "user__first_name", "user__email")
    raw_id_fields = ("user",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("course_code", "title", "department", "category", "course_type",
                    "credit", "year", "semester", "is_active")
    list_filter = ("category", "course_type", "year", "semester", "department")
    search_fields = ("course_code", "title")


@admin.register(CourseOffer)
class CourseOfferAdmin(admin.ModelAdmin):
    list_display = ("course", "teacher", "level", "year", "semester",
                    "calendar_year", "seat_capacity", "enrolled_count", "is_active")
    list_filter = ("level", "year", "semester", "calendar_year", "is_active")
    search_fields = ("course__course_code", "course__title")


@admin.register(EnrollmentDeadline)
class EnrollmentDeadlineAdmin(admin.ModelAdmin):
    list_display = ("exam_title", "level", "year", "semester", "calendar_year",
                    "start_date", "end_date", "late_end_date", "window_state", "is_open")
    list_filter = ("level", "year", "semester", "calendar_year", "is_open")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "offer", "enrollment_date", "status")
    list_filter = ("status", "offer__calendar_year", "offer__level", "offer__year")
    search_fields = ("student__student_id", "offer__course__course_code")
    raw_id_fields = ("student", "offer")


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "attendance_marks", "ct_marks", "final_marks",
                    "total", "grade", "gpa", "is_published")
    list_filter = ("is_published", "grade")
    raw_id_fields = ("enrollment",)


@admin.register(ExamRoutine)
class ExamRoutineAdmin(admin.ModelAdmin):
    list_display = ("offer", "exam_title", "exam_type", "exam_date", "start_time",
                    "exam_place", "memo_no", "is_published")
    list_filter = ("exam_type", "is_published", "exam_date")


@admin.register(ClassRoutine)
class ClassRoutineAdmin(admin.ModelAdmin):
    list_display = ("offer", "day", "start_time", "end_time", "room")
    list_filter = ("day",)


@admin.register(FormFillup)
class FormFillupAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "student", "deadline", "amount", "payment_status",
                    "approval_status", "is_late", "applied_at")
    list_filter = ("approval_status", "payment_status", "is_late")
    search_fields = ("invoice_no", "student__student_id")
    raw_id_fields = ("student",)


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "amount", "method", "status", "payment_date")
    list_filter = ("method", "status")
    search_fields = ("invoice_no", "transaction_id")


@admin.register(AdmitCard)
class AdmitCardAdmin(admin.ModelAdmin):
    list_display = ("serial_no", "student", "deadline", "issue_date", "is_released")
    list_filter = ("is_released",)
    search_fields = ("serial_no", "student__student_id")
    raw_id_fields = ("student",)
