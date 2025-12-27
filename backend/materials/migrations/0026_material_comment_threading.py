"""
Migration for Material Comment Threading (T_MAT_007)

Adds support for:
- Nested comment threading (parent_comment field)
- Soft delete (is_deleted flag)
- Moderation (is_approved flag)
- Timestamp tracking (deleted_at field)
- Database indexes for query optimization
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0022_add_search_history'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialcomment',
            name='parent_comment',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='replies',
                to='materials.materialcomment',
                verbose_name='Родительский комментарий',
            ),
        ),
        migrations.AddField(
            model_name='materialcomment',
            name='is_deleted',
            field=models.BooleanField(
                default=False,
                verbose_name='Удален',
            ),
        ),
        migrations.AddField(
            model_name='materialcomment',
            name='is_approved',
            field=models.BooleanField(
                default=True,
                verbose_name='Одобрен',
            ),
        ),
        migrations.AddField(
            model_name='materialcomment',
            name='deleted_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Дата удаления',
            ),
        ),
        migrations.AlterField(
            model_name='materialcomment',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
            ),
        ),
        migrations.AlterField(
            model_name='materialcomment',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
            ),
        ),
        migrations.AlterModelOptions(
            name='materialcomment',
            options={
                'ordering': ['created_at'],
                'verbose_name': 'Комментарий',
                'verbose_name_plural': 'Комментарии',
            },
        ),
        migrations.AddIndex(
            model_name='materialcomment',
            index=models.Index(
                fields=['material', 'parent_comment'],
                name='matcom_mat_parent_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='materialcomment',
            index=models.Index(
                fields=['author', 'material'],
                name='matcom_author_mat_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='materialcomment',
            index=models.Index(
                fields=['-created_at'],
                name='matcom_created_idx',
            ),
        ),
    ]
