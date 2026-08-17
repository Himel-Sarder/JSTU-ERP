from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0003_rename_course_level_to_year"),
    ]

    operations = [
        # Narrow the constraint before the column disappears.
        migrations.AlterUniqueTogether(
            name="courseoffer",
            unique_together={("course", "level", "semester", "year")},
        ),
        migrations.RemoveField(
            model_name="courseoffer",
            name="section",
        ),
    ]
