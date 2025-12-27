# Generated migration for T_MAT_008

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0027_add_material_download_log_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='submissionfile',
            name='file_checksum',
            field=models.CharField(
                blank=True,
                help_text='SHA256 hash для проверки целостности и обнаружения дубликатов',
                max_length=64,
                verbose_name='SHA256 контрольная сумма'
            ),
        ),
        migrations.AddIndex(
            model_name='submissionfile',
            index=models.Index(
                fields=['file_checksum', 'submission'],
                name='materials_s_file_ch_idx'
            ),
        ),
    ]
