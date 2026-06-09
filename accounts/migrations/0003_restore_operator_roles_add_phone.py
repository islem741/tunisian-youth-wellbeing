# Restores the Operator/Supervisor/Admin role model:
# - Adds back school and region fields
# - Removes peer-support-era fields (assigned_counselor, bio)
# - Resets role choices and default to Operator
# - Adds the new phone field

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_update_roles"),
    ]

    operations = [
        # 1. Restore school and region --------------------------------
        migrations.AddField(
            model_name="user",
            name="school",
            field=models.CharField(
                blank=True,
                max_length=100,
                help_text="School the Operator is attached to (scopes their visible students).",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="region",
            field=models.CharField(
                blank=True,
                max_length=80,
                help_text="Governorate / administrative region.",
            ),
        ),
        # 2. Add phone ------------------------------------------------
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True,
                max_length=20,
                help_text="Contact number (optional, for intervention coordination).",
            ),
        ),
        # 3. Reset role field to Operator/Supervisor/Admin ------------
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("operator",   "Operator (School staff)"),
                    ("supervisor", "Supervisor (Psychologist)"),
                    ("admin",      "Admin (Program manager)"),
                ],
                default="operator",
                help_text="Platform role. Controls workflow actions, not Django admin access.",
                max_length=20,
            ),
        ),
        # 4. Remove peer-support-era fields ---------------------------
        migrations.RemoveField(
            model_name="user",
            name="assigned_counselor",
        ),
        migrations.RemoveField(
            model_name="user",
            name="bio",
        ),
    ]
