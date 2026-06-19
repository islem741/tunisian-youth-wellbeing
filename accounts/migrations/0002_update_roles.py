# Hand-written migration: replace Operator/Supervisor/Admin roles with
# Youth/PeerSupporter/Counselor/Supervisor and swap school+region fields
# for assigned_counselor (FK) and bio (TextField).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        # 1. Add the two new fields -----------------------------------
        migrations.AddField(
            model_name="user",
            name="assigned_counselor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_youth",
                to=settings.AUTH_USER_MODEL,
                help_text="For Youth: the counselor assigned to this account.",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.TextField(
                blank=True,
                help_text="Brief background for peer supporters and counselors.",
            ),
        ),
        # 2. Alter the role field: new choices + new default ----------
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("youth", "Youth"),
                    ("peer_supporter", "Peer Supporter"),
                    ("counselor", "Professional Counselor"),
                    ("supervisor", "Supervisor"),
                ],
                default="youth",
                help_text="Platform role. Controls workflow actions, not Django admin access.",
                max_length=20,
            ),
        ),
        # 3. Remove the old fields ------------------------------------
        migrations.RemoveField(
            model_name="user",
            name="school",
        ),
        migrations.RemoveField(
            model_name="user",
            name="region",
        ),
    ]
