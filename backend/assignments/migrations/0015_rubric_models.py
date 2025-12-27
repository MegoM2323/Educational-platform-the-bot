# Generated migration for T_ASN_006: Assignment Rubric Support
# Creates GradingRubric, RubricCriterion, RubricScore, RubricTemplate models
# and adds rubric field to Assignment model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0014_add_optimization_indexes'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create GradingRubric model
        migrations.CreateModel(
            name='GradingRubric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Например: "Рубрика для оценки эссе"', max_length=255, verbose_name='Название рубрики')),
                ('description', models.TextField(blank=True, help_text='Подробное описание критериев оценивания', verbose_name='Описание рубрики')),
                ('is_template', models.BooleanField(default=False, help_text='Если включено, рубрика будет доступна как шаблон для других преподавателей', verbose_name='Является шаблоном')),
                ('total_points', models.PositiveIntegerField(default=100, help_text='Максимальное количество баллов по этой рубрике', verbose_name='Всего баллов')),
                ('is_deleted', models.BooleanField(default=False, help_text='Мягкое удаление - рубрика не отображается в списках', verbose_name='Удалено')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата изменения')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_rubrics', to=settings.AUTH_USER_MODEL, verbose_name='Создано')),
            ],
            options={
                'verbose_name': 'Рубрика оценивания',
                'verbose_name_plural': 'Рубрики оценивания',
                'ordering': ['-created_at'],
            },
        ),

        # Create RubricCriterion model
        migrations.CreateModel(
            name='RubricCriterion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Например: "Качество содержания"', max_length=255, verbose_name='Название критерия')),
                ('description', models.TextField(help_text='Что оценивает этот критерий', verbose_name='Описание критерия')),
                ('max_points', models.PositiveIntegerField(help_text='Максимальное количество баллов за этот критерий', verbose_name='Максимум баллов')),
                ('point_scales', models.JSONField(default=list, help_text='Массив [баллы, описание] для каждого уровня выполнения', verbose_name='Шкала оценивания')),
                ('order', models.PositiveIntegerField(default=0, help_text='Порядок отображения критерия в рубрике', verbose_name='Порядок')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('rubric', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='criteria', to='assignments.gradingrubric', verbose_name='Рубрика')),
            ],
            options={
                'verbose_name': 'Критерий рубрики',
                'verbose_name_plural': 'Критерии рубрики',
                'ordering': ['order'],
            },
        ),

        # Create RubricScore model
        migrations.CreateModel(
            name='RubricScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Баллы')),
                ('comment', models.TextField(blank=True, help_text='Объяснение выставленной оценки', verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата изменения')),
                ('criterion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scores', to='assignments.rubriccriterion', verbose_name='Критерий рубрики')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rubric_scores', to='assignments.assignmentsubmission', verbose_name='Ответ на задание')),
            ],
            options={
                'verbose_name': 'Оценка по критерию',
                'verbose_name_plural': 'Оценки по критериям',
                'ordering': ['criterion__order'],
            },
        ),

        # Create RubricTemplate model
        migrations.CreateModel(
            name='RubricTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название шаблона')),
                ('description', models.TextField(blank=True, verbose_name='Описание шаблона')),
                ('assignment_type', models.CharField(choices=[('essay', 'Эссе'), ('project', 'Проект'), ('presentation', 'Презентация'), ('research_paper', 'Исследовательская работа'), ('coding', 'Программирование'), ('creative', 'Творческая работа'), ('practical', 'Практическая работа')], max_length=50, verbose_name='Тип задания')),
                ('is_system', models.BooleanField(default=True, help_text='Создан администратором, доступен всем', verbose_name='Системный шаблон')),
                ('is_active', models.BooleanField(default=True, help_text='Активные шаблоны отображаются в списке доступных', verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rubric', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='template', to='assignments.gradingrubric', verbose_name='Рубрика')),
            ],
            options={
                'verbose_name': 'Шаблон рубрики',
                'verbose_name_plural': 'Шаблоны рубрик',
                'ordering': ['assignment_type', 'name'],
            },
        ),

        # Add rubric field to Assignment
        migrations.AddField(
            model_name='assignment',
            name='rubric',
            field=models.ForeignKey(blank=True, help_text='Опциональная рубрика для структурированного оценивания', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignments', to='assignments.gradingrubric', verbose_name='Рубрика оценивания'),
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='gradingrubric',
            index=models.Index(fields=['created_by', '-created_at'], name='rubric_created_by_idx'),
        ),
        migrations.AddIndex(
            model_name='gradingrubric',
            index=models.Index(fields=['is_template', 'is_deleted'], name='rubric_template_deleted_idx'),
        ),
        migrations.AddIndex(
            model_name='rubriccriterion',
            index=models.Index(fields=['rubric', 'order'], name='criterion_rubric_order_idx'),
        ),
        migrations.AddIndex(
            model_name='rubricscore',
            index=models.Index(fields=['submission', 'criterion'], name='score_submission_criterion_idx'),
        ),

        # Add unique constraints
        migrations.AlterUniqueTogether(
            name='rubriccriterion',
            unique_together={('rubric', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='rubricscore',
            unique_together={('submission', 'criterion')},
        ),
        migrations.AlterUniqueTogether(
            name='rubrictemplate',
            unique_together={('assignment_type', 'name')},
        ),
    ]
