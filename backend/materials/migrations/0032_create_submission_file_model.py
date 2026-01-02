# Generated migration for T_MAT_008 - SubmissionFile model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0029_add_optimization_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='submissions/files/', verbose_name='Файл')),
                ('original_filename', models.CharField(max_length=255, verbose_name='Исходное имя файла')),
                ('file_size', models.PositiveIntegerField(verbose_name='Размер файла (байт)')),
                ('file_type', models.CharField(help_text='Расширение файла (pdf, doc, jpg и т.д.)', max_length=20, verbose_name='Тип файла')),
                ('mime_type', models.CharField(blank=True, max_length=100, verbose_name='MIME тип файла')),
                ('file_checksum', models.CharField(blank=True, help_text='SHA256 hash для проверки целостности и обнаружения дубликатов', max_length=64, verbose_name='SHA256 контрольная сумма')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='materials.materialsubmission', verbose_name='Ответ на материал')),
            ],
            options={
                'verbose_name': 'Файл ответа на материал',
                'verbose_name_plural': 'Файлы ответов на материалы',
                'ordering': ['uploaded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='submissionfile',
            index=models.Index(fields=['submission', 'uploaded_at'], name='materials_s_submiss_idx'),
        ),
        migrations.AddIndex(
            model_name='submissionfile',
            index=models.Index(fields=['file_checksum', 'submission'], name='materials_s_file_ch_idx'),
        ),
    ]
