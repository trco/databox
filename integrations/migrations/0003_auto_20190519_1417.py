# Generated by Django 2.2.1 on 2019-05-19 14:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0002_githuboauth2token'),
    ]

    operations = [
        migrations.RenameField(
            model_name='githuboauth2token',
            old_name='refresh_token',
            new_name='token_type',
        ),
        migrations.RemoveField(
            model_name='githuboauth2token',
            name='expires',
        ),
    ]
