"""Split the old CourseOffer.level/year pair into three explicit columns.

Before: level = year of study (1-5), year = calendar year (2026).
After:  level = degree level (BSC/MS/PHD), year = year of study (1-4),
        calendar_year = calendar year (2026).

The renames are ordered so the existing study-year values land in `year`
and the calendar values land in `calendar_year` - no data is lost.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0004_remove_courseoffer_section"),
    ]

    operations = [
        # The constraint names the columns about to move; drop it first.
        migrations.AlterUniqueTogether(
            name="courseoffer",
            unique_together=set(),
        ),
        # Free up the name `year` before reusing it for the study year.
        migrations.RenameField(
            model_name="courseoffer",
            old_name="year",
            new_name="calendar_year",
        ),
        migrations.RenameField(
            model_name="courseoffer",
            old_name="level",
            new_name="year",
        ),
        migrations.AlterField(
            model_name="courseoffer",
            name="year",
            field=models.PositiveSmallIntegerField(
                default=1, help_text="Year of study - 1st to 4th."),
        ),
        migrations.AlterField(
            model_name="courseoffer",
            name="calendar_year",
            field=models.PositiveIntegerField(
                default=2026, help_text="The running calendar year, e.g. 2026."),
        ),
        # `level` is now the degree level and starts fresh.
        migrations.AddField(
            model_name="courseoffer",
            name="level",
            field=models.CharField(
                choices=[("BSC", "Bachelor"), ("MS", "M.S. / MBA"), ("PHD", "PhD")],
                default="BSC",
                help_text="Degree level - Bachelor, M.S. or PhD.",
                max_length=4,
            ),
        ),
        migrations.AlterModelOptions(
            name="courseoffer",
            options={"ordering": ["-calendar_year", "level", "year", "semester",
                                  "course__course_code"]},
        ),
        migrations.AlterUniqueTogether(
            name="courseoffer",
            unique_together={("course", "level", "year", "semester", "calendar_year")},
        ),
    ]
