from django.urls import path

from . import views

app_name = "teacherpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("marks/", views.marks, name="marks"),
    path("postgraduate/", views.pg_marks, name="pg_marks"),
    path("class-routine/", views.class_routine, name="class_routine"),
    path("exam-routine/", views.exam_routine, name="exam_routine"),
    path("students/", views.students, name="students"),
    path("leave/", views.leave, name="leave"),
    path("house-allotment/", views.house, name="house"),
    path("vehicle/", views.vehicle, name="vehicle"),
    path("events/", views.events, name="events"),
    path("research/", views.research, name="research"),
    path("publications/", views.publications, name="publications"),
    path("remuneration/", views.remuneration, name="remuneration"),
    path("baures/", views.baures, name="baures"),
    path("notices/", views.notices, name="notices"),
]
