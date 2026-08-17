from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="course",
            old_name="level",
            new_name="year",
        ),
    ]
