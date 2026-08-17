"""Give EnrollmentDeadline the same three columns as CourseOffer.

Before: level = year of study (1-5), year = calendar year (2026).
After:  level = degree level (BSC/MS/PHD), year = year of study (1-4),
        calendar_year = calendar year (2026).

Mirrors academics.0005 - the renames are ordered so existing values land in
the column that keeps their meaning.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0005_courseoffer_level_year_calendar_year"),
    ]

    operations = [
        # Free up the name `year` before reusing it for the study year.
        migrations.RenameField(
            model_name="enrollmentdeadline",
            old_name="year",
            new_name="calendar_year",
        ),
        migrations.RenameField(
            model_name="enrollmentdeadline",
            old_name="level",
            new_name="year",
        ),
        migrations.AlterField(
            model_name="enrollmentdeadline",
            name="year",
            field=models.PositiveSmallIntegerField(
                default=1, help_text="Year of study - 1st to 4th."),
        ),
        migrations.AlterField(
            model_name="enrollmentdeadline",
            name="calendar_year",
            field=models.PositiveIntegerField(
                default=2026, help_text="The running calendar year, e.g. 2026."),
        ),
        # `level` is now the degree level and starts fresh.
        migrations.AddField(
            model_name="enrollmentdeadline",
            name="level",
            field=models.CharField(
                choices=[("BSC", "Bachelor"), ("MS", "M.S. / MBA"), ("PHD", "PhD")],
                default="BSC",
                help_text="Degree level - Bachelor, M.S. or PhD.",
                max_length=4,
            ),
        ),
        migrations.AlterModelOptions(
            name="enrollmentdeadline",
            options={"ordering": ["-calendar_year", "level", "year", "semester"],
                     "verbose_name": "enrollment deadline"},
        ),
    ]
