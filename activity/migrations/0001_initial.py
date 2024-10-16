# Generated by Django 5.1.1 on 2024-10-10 09:45

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserActivityLog',
            fields=[
                ('log_id', models.AutoField(primary_key=True, serialize=False)),
                ('activity_type', models.CharField(choices=[('login', 'Login'), ('course_completion', 'Course Completion'), ('logout', 'Logout'), ('page_visit', 'Page Visit')], max_length=100)),
                ('activity_details', models.TextField(blank=True, null=True)),
                ('activity_timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
