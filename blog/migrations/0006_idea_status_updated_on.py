# Generated migration to add status and updated_on fields to Idea model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0005_delete_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='idea',
            name='status',
            field=models.IntegerField(choices=[(0, 'Draft'), (1, 'Published')], default=0),
        ),
        migrations.AddField(
            model_name='idea',
            name='updated_on',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
