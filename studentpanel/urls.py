from django.urls import path

from . import views

app_name = "studentpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("guardian/", views.guardian, name="guardian"),
    path("bank/", views.bank, name="bank"),
    path("id-card/", views.id_card, name="id_card"),
    path("network/", views.network, name="network"),
    path("email/", views.email, name="email"),
    path("notices/", views.notices, name="notices"),
    path("admit-card/", views.admit_card, name="admit_card"),
    path("results/", views.results, name="results"),
    path("enrollments/", views.enrollments, name="enrollments"),
    path("form-fillup/", views.form_fillup, name="form_fillup"),
    path("form-fillup/apply/<int:pk>/", views.form_fillup_action, name="form_fillup_action"),
    path("form-fillup/payment/<int:pk>/", views.form_fillup_payment,
         name="form_fillup_payment"),
    path("invoices/", views.invoices, name="invoices"),
    path("complaints/", views.complaints, name="complaints"),
    path("feedback/", views.feedback, name="feedback"),
    path("awards/", views.awards, name="awards"),
    path("support/", views.support, name="support"),
]
