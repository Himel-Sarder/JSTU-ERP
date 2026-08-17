from django.contrib import admin

from .models import (Award, ComplaintSuggestion, CourseFeedback, Event,
                     ExamRemuneration, HouseAllotment, LeaveApplication, Notice,
                     PostgraduateApplication, Publication, ResearchPost,
                     VehicleRequisition, WebsiteMenu)


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "audience", "post_date", "is_pinned", "is_published")
    list_filter = ("category", "audience", "is_published", "is_pinned")
    search_fields = ("title", "body")


@admin.register(WebsiteMenu)
class WebsiteMenuAdmin(admin.ModelAdmin):
    list_display = ("page_title", "menu_order", "parent", "status", "external_link")
    list_filter = ("status",)
    search_fields = ("page_title",)


@admin.register(ComplaintSuggestion)
class ComplaintSuggestionAdmin(admin.ModelAdmin):
    list_display = ("tracking_code", "subject", "kind", "report_to", "submitted_by",
                    "status", "created_at")
    list_filter = ("kind", "report_to", "status", "is_anonymous")
    search_fields = ("tracking_code", "subject")
    readonly_fields = ("tracking_code", "created_at")


@admin.register(CourseFeedback)
class CourseFeedbackAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "question_no", "rating", "submitted_at")
    list_filter = ("rating",)


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ("title", "student", "category", "year", "awarded_by")
    list_filter = ("category", "year")


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ("teacher", "leave_type", "from_date", "to_date", "days", "status")
    list_filter = ("leave_type", "status")


@admin.register(HouseAllotment)
class HouseAllotmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "house_category", "preferred_quarter", "status", "applied_at")
    list_filter = ("house_category", "status")


@admin.register(VehicleRequisition)
class VehicleRequisitionAdmin(admin.ModelAdmin):
    list_display = ("teacher", "vehicle_type", "destination", "journey_date",
                    "passengers", "status")
    list_filter = ("vehicle_type", "status")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "organizer", "venue", "start_at", "is_published")
    list_filter = ("kind", "is_published")


@admin.register(ResearchPost)
class ResearchPostAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "category", "published_at", "is_published")
    list_filter = ("category", "is_published")


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "kind", "journal_name", "year",
                    "indexing", "in_baures")
    list_filter = ("kind", "year", "in_baures")
    search_fields = ("title", "journal_name")


@admin.register(ExamRemuneration)
class ExamRemunerationAdmin(admin.ModelAdmin):
    list_display = ("teacher", "exam_title", "amount", "status", "bill_date", "paid_date")
    list_filter = ("status",)


@admin.register(PostgraduateApplication)
class PostgraduateApplicationAdmin(admin.ModelAdmin):
    list_display = ("research_title", "student", "supervisor", "program", "status")
    list_filter = ("program", "status")
