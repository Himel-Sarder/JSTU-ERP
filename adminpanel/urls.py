from django.urls import path

from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("courses/add/", views.add_course, name="add_course"),
    path("courses/offer/", views.course_offer, name="course_offer"),
    path("enrollment-deadline/", views.deadline, name="deadline"),
    path("routine/", views.routine, name="routine"),
    path("exam-schedule/", views.exam_schedule, name="exam_schedule"),
    path("form-fillup/", views.fillup, name="fillup"),
    path("students/", views.student_status, name="student_status"),
    path("approvals/", views.approvals, name="approvals"),
    path("admit-cards/", views.admit_cards, name="admit_cards"),
    path("reports/", views.reports, name="reports"),
    path("website/", views.website, name="website"),
    path("notices/", views.notices, name="notices"),
    path("complaints/", views.complaints, name="complaints"),
    path("requests/", views.requests_queue, name="requests"),
    path("users/", views.users, name="users"),
    path("audit/", views.audit, name="audit"),
]
