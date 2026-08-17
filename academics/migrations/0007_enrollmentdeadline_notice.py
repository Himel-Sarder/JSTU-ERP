"""Replace EnrollmentDeadline.memo_no with an optional notice + attachment.

The two existing rows carry memo numbers, so those are copied into the new
`notice` text before the old column is dropped - nothing is lost.
"""

import django.core.validators
from django.db import migrations, models


def memo_to_notice(apps, schema_editor):
    Deadline = apps.get_model("academics", "EnrollmentDeadline")
    for row in Deadline.objects.exclude(memo_no="").exclude(memo_no=None):
        row.notice = f"Memo no. {row.memo_no}"
        row.save(update_fields=["notice"])


def notice_to_memo(apps, schema_editor):
    """Best-effort reverse: put the notice text back in memo_no (truncated)."""
    Deadline = apps.get_model("academics", "EnrollmentDeadline")
    for row in Deadline.objects.exclude(notice=""):
        row.memo_no = row.notice[:40]
        row.save(update_fields=["memo_no"])


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0006_enrollmentdeadline_level_year_calendar_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="enrollmentdeadline",
            name="notice",
            field=models.TextField(
                blank=True, help_text="Optional notice shown to students."),
        ),
        migrations.AddField(
            model_name="enrollmentdeadline",
            name="notice_file",
            field=models.FileField(
                blank=True, null=True, upload_to="notices/",
                help_text="Optional PDF or image attachment.",
                validators=[django.core.validators.FileExtensionValidator(
                    ["pdf", "png", "jpg", "jpeg", "webp"])],
            ),
        ),
        migrations.RunPython(memo_to_notice, notice_to_memo),
        migrations.RemoveField(
            model_name="enrollmentdeadline",
            name="memo_no",
        ),
    ]
