# Generated by Django 5.1.11 on 2025-07-05 20:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('forms', '0003_alter_newslettersignuppage_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='newslettersignuppage',
            name='unsubscribe_button_text',
            field=models.CharField(default='Unsubscribe', help_text='Text for the unsubscribe button', max_length=50),
        ),
    ]
