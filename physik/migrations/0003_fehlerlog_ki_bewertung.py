from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('physik', '0002_delete_profil'),
    ]

    operations = [
        migrations.AddField(
            model_name='fehlerlog',
            name='ki_bewertung',
            field=models.BooleanField(
                blank=True,
                default=None,
                help_text='Ob die KI die Antwort als richtig bewertet hat (True=richtig, False=falsch, None=nicht geprüft)',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='fehlerlog',
            name='ki_hinweis',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Rückmeldung der KI zur Bewertung'
            ),
        ),
    ]
