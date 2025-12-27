# Generated migration for report template system enhancements

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0008_add_optimization_indexes'),
    ]

    operations = [
        # Add new fields to ReportTemplate
        migrations.AddField(
            model_name='reporttemplate',
            name='sections',
            field=models.JSONField(blank=True, default=list, help_text='List of sections included in template: [{"name": "summary", "fields": [...]}]', verbose_name='Секции отчета'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='layout_config',
            field=models.JSONField(blank=True, default=dict, help_text='Layout settings: orientation, page_size, margins, header, footer, etc.', verbose_name='Конфигурация макета'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='default_format',
            field=models.CharField(choices=[('pdf', 'PDF'), ('excel', 'Excel'), ('json', 'JSON'), ('csv', 'CSV')], default='pdf', max_length=10, verbose_name='Формат экспорта по умолчанию'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='parent_template',
            field=models.ForeignKey(blank=True, help_text='Template this one is inherited from', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_templates', to='reports.reporttemplate', verbose_name='Родительский шаблон'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='version',
            field=models.PositiveIntegerField(default=1, verbose_name='Версия'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='previous_version',
            field=models.ForeignKey(blank=True, help_text='Previous version of this template', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='next_versions', to='reports.reporttemplate', verbose_name='Предыдущая версия'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='is_archived',
            field=models.BooleanField(default=False, verbose_name='Архивирован'),
        ),
        migrations.AddField(
            model_name='reporttemplate',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата архивирования'),
        ),
        # Update template_content to allow blank values
        migrations.AlterField(
            model_name='reporttemplate',
            name='template_content',
            field=models.JSONField(blank=True, default=dict, verbose_name='Содержание шаблона'),
        ),
        # Add indexes for performance
        migrations.AddIndex(
            model_name='reporttemplate',
            index=models.Index(fields=['type', 'is_default'], name='reports_rep_type_i_idx'),
        ),
        migrations.AddIndex(
            model_name='reporttemplate',
            index=models.Index(fields=['created_by', '-created_at'], name='reports_rep_created_idx'),
        ),
        migrations.AddIndex(
            model_name='reporttemplate',
            index=models.Index(fields=['parent_template', 'is_archived'], name='reports_rep_parent_idx'),
        ),
    ]
