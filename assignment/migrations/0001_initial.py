# Generated by Django 5.1.1 on 2024-10-25 14:49

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Assignment',
            fields=[
                ('assignment_id', models.IntegerField(primary_key=True, serialize=False)),
                ('assignment_name', models.CharField(max_length=100)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
            ],
        ),
    ]
