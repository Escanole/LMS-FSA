# Generated by Django 5.0.9 on 2024-11-28 13:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feedback", "0004_coursefeedback_feedback_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="coursefeedback",
            old_name="comments",
            new_name="course_comment",
        ),
        migrations.RemoveField(
            model_name="coursefeedback",
            name="feedback_type",
        ),
        migrations.AddField(
            model_name="coursefeedback",
            name="material_comment",
            field=models.TextField(blank=True, null=True),
        ),
    ]
