from django import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('blog', '001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('content', models.TextField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(choices=[(0, 'Draft'), (1, 'Published')], default=0)),
            ],
        ),
    ]   

    operations = [
        migrations.addfield(
            model_name='post',
            name='excerpt',
            field=models.TextField(default='', max_length=200),
                ),
    ]