"""
Management команда для очистки базы данных от мусорных данных
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, models
from django.conf import settings
import os
from datetime import timedelta
import re

User = get_user_model()


class Command(BaseCommand):
    help = 'Очищает базу данных от мусорных данных и учетных записей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет удалено без фактического удаления'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Выполнить все типы очистки'
        )
        parser.add_argument(
            '--users',
            action='store_true',
            help='Очистить тестовых/мусорных пользователей'
        )
        parser.add_argument(
            '--applications',
            action='store_true',
            help='Очистить старые заявки'
        )
        parser.add_argument(
            '--chat',
            action='store_true',
            help='Очистить старые сообщения и пустые чаты'
        )
        parser.add_argument(
            '--drafts',
            action='store_true',
            help='Очистить старые черновики'
        )
        parser.add_argument(
            '--notifications',
            action='store_true',
            help='Очистить старые уведомления'
        )
        parser.add_argument(
            '--files',
            action='store_true',
            help='Очистить неиспользуемые файлы'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Количество дней для определения "старых" записей (по умолчанию 90)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное удаление без подтверждения'
        )

    def handle(self, *args, **options):
        # Проверяем, что хотя бы один тип очистки выбран
        if not any([
            options['all'],
            options['users'],
            options['applications'],
            options['chat'],
            options['drafts'],
            options['notifications'],
            options['files']
        ]):
            self.stdout.write(self.style.WARNING(
                'Не указан тип очистки. Используйте --all или выберите конкретные типы (--users, --applications, и т.д.)\n'
                'Используйте --help для справки.'
            ))
            return

        dry_run = options['dry_run']
        days = options['days']
        force = options['force']
        all_cleanup = options['all']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== РЕЖИМ ПРОСМОТРА (dry-run) ==='))
            self.stdout.write(self.style.WARNING('Ничего не будет удалено\n'))

        stats = {
            'users': 0,
            'applications': 0,
            'chat_messages': 0,
            'chat_rooms': 0,
            'drafts': 0,
            'notifications': 0,
            'files': 0,
        }

        try:
            if all_cleanup or options['users']:
                stats['users'] = self.cleanup_users(dry_run, days, force)

            if all_cleanup or options['applications']:
                stats['applications'] = self.cleanup_applications(dry_run, days, force)

            if all_cleanup or options['chat']:
                chat_stats = self.cleanup_chat(dry_run, days, force)
                stats['chat_messages'] = chat_stats['messages']
                stats['chat_rooms'] = chat_stats['rooms']

            if all_cleanup or options['drafts']:
                stats['drafts'] = self.cleanup_drafts(dry_run, days, force)

            if all_cleanup or options['notifications']:
                stats['notifications'] = self.cleanup_notifications(dry_run, days, force)

            if all_cleanup or options['files']:
                stats['files'] = self.cleanup_files(dry_run, force)

            # Выводим статистику
            self.print_stats(stats, dry_run)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при очистке: {e}'))
            raise CommandError(f'Очистка не завершена: {e}')

    def cleanup_users(self, dry_run, days, force):
        """Очистка тестовых и мусорных пользователей"""
        self.stdout.write('\n=== Очистка пользователей ===')
        
        # Паттерны для определения тестовых пользователей
        test_patterns = [
            r'^test',
            r'^Test',
            r'^тест',
            r'^Тест',
            r'test@',
            r'Test@',
            r'тест@',
            r'Тест@',
            r'example\.com',
            r'@test\.',
            r'^user\d+$',
            r'^User\d+$',
        ]
        
        # Пользователи без email или с невалидными email
        users_to_delete = User.objects.filter(
            email__isnull=True
        ) | User.objects.filter(
            email=''
        )
        
        # Пользователи с тестовыми именами/email
        for pattern in test_patterns:
            users_to_delete = users_to_delete | User.objects.filter(
                username__iregex=pattern
            ) | User.objects.filter(
                email__iregex=pattern
            )
        
        # Пользователи без профилей, созданные давно
        from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
        
        old_date = timezone.now() - timedelta(days=days)
        users_without_profiles = User.objects.filter(
            created_at__lt=old_date
        ).exclude(
            id__in=StudentProfile.objects.values_list('user_id', flat=True)
        ).exclude(
            id__in=TeacherProfile.objects.values_list('user_id', flat=True)
        ).exclude(
            id__in=TutorProfile.objects.values_list('user_id', flat=True)
        ).exclude(
            id__in=ParentProfile.objects.values_list('user_id', flat=True)
        )
        
        users_to_delete = users_to_delete | users_without_profiles
        
        # Исключаем суперпользователей
        users_to_delete = users_to_delete.exclude(is_superuser=True)
        
        # Удаляем дубликаты
        users_to_delete = users_to_delete.distinct()
        
        count = users_to_delete.count()
        
        if count > 0:
            self.stdout.write(f'Найдено пользователей для удаления: {count}')
            if not dry_run:
                if not self.confirm(f'Удалить {count} пользователей?', force_confirm=force):
                    return 0
                
                with transaction.atomic():
                    deleted_count = users_to_delete.count()
                    users_to_delete.delete()
                    self.stdout.write(self.style.SUCCESS(f'Удалено пользователей: {deleted_count}'))
                    return deleted_count
            else:
                for user in users_to_delete[:10]:  # Показываем первые 10
                    self.stdout.write(f'  - {user.username} ({user.email}) [{user.role}]')
                if count > 10:
                    self.stdout.write(f'  ... и еще {count - 10} пользователей')
                return count
        else:
            self.stdout.write('Пользователей для удаления не найдено')
            return 0

    def cleanup_applications(self, dry_run, days, force):
        """Очистка старых заявок"""
        self.stdout.write('\n=== Очистка заявок ===')
        
        from applications.models import Application
        
        old_date = timezone.now() - timedelta(days=days)
        
        # Старые обработанные заявки (одобренные или отклоненные)
        applications_to_delete = Application.objects.filter(
            status__in=[Application.Status.APPROVED, Application.Status.REJECTED],
            processed_at__lt=old_date
        )
        
        count = applications_to_delete.count()
        
        if count > 0:
            self.stdout.write(f'Найдено заявок для удаления: {count}')
            if not dry_run:
                if not self.confirm(f'Удалить {count} заявок?', force_confirm=force):
                    return 0
                
                with transaction.atomic():
                    deleted_count = applications_to_delete.count()
                    applications_to_delete.delete()
                    self.stdout.write(self.style.SUCCESS(f'Удалено заявок: {deleted_count}'))
                    return deleted_count
            else:
                return count
        else:
            self.stdout.write('Заявок для удаления не найдено')
            return 0

    def cleanup_chat(self, dry_run, days, force):
        """Очистка старых сообщений и пустых чатов"""
        self.stdout.write('\n=== Очистка чата ===')
        
        from chat.models import Message, ChatRoom
        
        old_date = timezone.now() - timedelta(days=days)
        
        # Старые сообщения
        messages_to_delete = Message.objects.filter(
            created_at__lt=old_date
        )
        
        messages_count = messages_to_delete.count()
        
        # Пустые чат-комнаты (без сообщений)
        empty_rooms = ChatRoom.objects.annotate(
            message_count=models.Count('messages')
        ).filter(
            message_count=0,
            created_at__lt=old_date
        )
        
        rooms_count = empty_rooms.count()
        
        stats = {'messages': 0, 'rooms': 0}
        
        if messages_count > 0:
            self.stdout.write(f'Найдено сообщений для удаления: {messages_count}')
            if not dry_run:
                if self.confirm(f'Удалить {messages_count} сообщений?', force_confirm=force):
                    with transaction.atomic():
                        deleted_count = messages_to_delete.count()
                        messages_to_delete.delete()
                        self.stdout.write(self.style.SUCCESS(f'Удалено сообщений: {deleted_count}'))
                        stats['messages'] = deleted_count
            else:
                stats['messages'] = messages_count
        
        if rooms_count > 0:
            self.stdout.write(f'Найдено пустых чат-комнат для удаления: {rooms_count}')
            if not dry_run:
                if self.confirm(f'Удалить {rooms_count} пустых чат-комнат?', force_confirm=force):
                    with transaction.atomic():
                        deleted_count = empty_rooms.count()
                        empty_rooms.delete()
                        self.stdout.write(self.style.SUCCESS(f'Удалено чат-комнат: {deleted_count}'))
                        stats['rooms'] = deleted_count
            else:
                stats['rooms'] = rooms_count
        
        if messages_count == 0 and rooms_count == 0:
            self.stdout.write('Данных чата для удаления не найдено')
        
        return stats

    def cleanup_drafts(self, dry_run, days, force):
        """Очистка старых черновиков"""
        self.stdout.write('\n=== Очистка черновиков ===')
        
        old_date = timezone.now() - timedelta(days=days)
        total_deleted = 0
        
        # Черновики материалов
        from materials.models import Material
        material_drafts = Material.objects.filter(
            status=Material.Status.DRAFT,
            updated_at__lt=old_date
        )
        material_count = material_drafts.count()
        
        # Черновики заданий
        from assignments.models import Assignment
        assignment_drafts = Assignment.objects.filter(
            status=Assignment.Status.DRAFT,
            updated_at__lt=old_date
        )
        assignment_count = assignment_drafts.count()
        
        # Черновики отчетов
        from reports.models import Report, StudentReport, TutorWeeklyReport, TeacherWeeklyReport
        report_drafts = Report.objects.filter(
            status=Report.Status.DRAFT,
            updated_at__lt=old_date
        )
        report_count = report_drafts.count()
        
        student_report_drafts = StudentReport.objects.filter(
            status=StudentReport.Status.DRAFT,
            updated_at__lt=old_date
        )
        student_report_count = student_report_drafts.count()
        
        tutor_report_drafts = TutorWeeklyReport.objects.filter(
            status=TutorWeeklyReport.Status.DRAFT,
            updated_at__lt=old_date
        )
        tutor_report_count = tutor_report_drafts.count()
        
        teacher_report_drafts = TeacherWeeklyReport.objects.filter(
            status=TeacherWeeklyReport.Status.DRAFT,
            updated_at__lt=old_date
        )
        teacher_report_count = teacher_report_drafts.count()
        
        total_count = material_count + assignment_count + report_count + student_report_count + tutor_report_count + teacher_report_count
        
        if total_count > 0:
            self.stdout.write(f'Найдено черновиков для удаления: {total_count}')
            self.stdout.write(f'  - Материалы: {material_count}')
            self.stdout.write(f'  - Задания: {assignment_count}')
            self.stdout.write(f'  - Отчеты: {report_count + student_report_count + tutor_report_count + teacher_report_count}')
            
            if not dry_run:
                if self.confirm(f'Удалить {total_count} черновиков?', force_confirm=force):
                    with transaction.atomic():
                        if material_count > 0:
                            deleted = material_drafts.count()
                            material_drafts.delete()
                            total_deleted += deleted
                        
                        if assignment_count > 0:
                            deleted = assignment_drafts.count()
                            assignment_drafts.delete()
                            total_deleted += deleted
                        
                        if report_count > 0:
                            deleted = report_drafts.count()
                            report_drafts.delete()
                            total_deleted += deleted
                        
                        if student_report_count > 0:
                            deleted = student_report_drafts.count()
                            student_report_drafts.delete()
                            total_deleted += deleted
                        
                        if tutor_report_count > 0:
                            deleted = tutor_report_drafts.count()
                            tutor_report_drafts.delete()
                            total_deleted += deleted
                        
                        if teacher_report_count > 0:
                            deleted = teacher_report_drafts.count()
                            teacher_report_drafts.delete()
                            total_deleted += deleted
                        
                        self.stdout.write(self.style.SUCCESS(f'Удалено черновиков: {total_deleted}'))
                        return total_deleted
            else:
                return total_count
        else:
            self.stdout.write('Черновиков для удаления не найдено')
            return 0

    def cleanup_notifications(self, dry_run, days, force):
        """Очистка старых уведомлений"""
        self.stdout.write('\n=== Очистка уведомлений ===')
        
        from notifications.models import Notification
        
        old_date = timezone.now() - timedelta(days=days)
        
        # Старые прочитанные уведомления
        notifications_to_delete = Notification.objects.filter(
            is_read=True,
            read_at__lt=old_date
        )
        
        count = notifications_to_delete.count()
        
        if count > 0:
            self.stdout.write(f'Найдено уведомлений для удаления: {count}')
            if not dry_run:
                if self.confirm(f'Удалить {count} уведомлений?', force_confirm=force):
                    with transaction.atomic():
                        deleted_count = notifications_to_delete.count()
                        notifications_to_delete.delete()
                        self.stdout.write(self.style.SUCCESS(f'Удалено уведомлений: {deleted_count}'))
                        return deleted_count
            else:
                return count
        else:
            self.stdout.write('Уведомлений для удаления не найдено')
            return 0

    def cleanup_files(self, dry_run, force):
        """Очистка неиспользуемых файлов"""
        self.stdout.write('\n=== Очистка файлов ===')
        
        if not hasattr(settings, 'MEDIA_ROOT') or not settings.MEDIA_ROOT:
            self.stdout.write(self.style.WARNING('MEDIA_ROOT не настроен, пропускаем очистку файлов'))
            return 0
        
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            self.stdout.write(self.style.WARNING(f'Директория {media_root} не существует'))
            return 0
        
        deleted_files = 0
        deleted_size = 0
        
        # Собираем все используемые файлы из моделей
        used_files = set()
        
        # Файлы из User (аватары)
        for user in User.objects.exclude(avatar='').exclude(avatar__isnull=True):
            if user.avatar:
                used_files.add(user.avatar.name)
        
        # Файлы из Material
        from materials.models import Material
        for material in Material.objects.exclude(file='').exclude(file__isnull=True):
            if material.file:
                used_files.add(material.file.name)
        
        # Файлы из MaterialSubmission
        from materials.models import MaterialSubmission
        for submission in MaterialSubmission.objects.exclude(submission_file='').exclude(submission_file__isnull=True):
            if submission.submission_file:
                used_files.add(submission.submission_file.name)
        
        # Файлы из AssignmentSubmission
        from assignments.models import AssignmentSubmission
        for submission in AssignmentSubmission.objects.exclude(file='').exclude(file__isnull=True):
            if submission.file:
                used_files.add(submission.file.name)
        
        # Файлы из Message
        from chat.models import Message
        for message in Message.objects.exclude(file='').exclude(file__isnull=True):
            if message.file:
                used_files.add(message.file.name)
            if message.image:
                used_files.add(message.image.name)
        
        # Файлы из Report
        from reports.models import Report, StudentReport, TutorWeeklyReport, TeacherWeeklyReport
        for report in Report.objects.exclude(file='').exclude(file__isnull=True):
            if report.file:
                used_files.add(report.file.name)
        
        for report in StudentReport.objects.exclude(attachment='').exclude(attachment__isnull=True):
            if report.attachment:
                used_files.add(report.attachment.name)
        
        for report in TutorWeeklyReport.objects.exclude(attachment='').exclude(attachment__isnull=True):
            if report.attachment:
                used_files.add(report.attachment.name)
        
        for report in TeacherWeeklyReport.objects.exclude(attachment='').exclude(attachment__isnull=True):
            if report.attachment:
                used_files.add(report.attachment.name)
        
        # Файлы из StudyPlanFile
        from materials.models import StudyPlanFile
        for plan_file in StudyPlanFile.objects.all():
            if plan_file.file:
                used_files.add(plan_file.file.name)
        
        # Ищем неиспользуемые файлы
        from pathlib import Path
        
        media_path = Path(media_root)
        unused_files = []
        
        for root, dirs, files in os.walk(media_root):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(media_path)
                
                # Проверяем, используется ли файл
                file_str = str(relative_path).replace('\\', '/')
                if file_str not in used_files:
                    unused_files.append(file_path)
        
        count = len(unused_files)
        
        if count > 0:
            # Вычисляем размер
            total_size = sum(f.stat().st_size for f in unused_files if f.exists())
            size_mb = total_size / (1024 * 1024)
            
            self.stdout.write(f'Найдено неиспользуемых файлов: {count}')
            self.stdout.write(f'Размер: {size_mb:.2f} MB')
            
            if not dry_run:
                if self.confirm(f'Удалить {count} файлов ({size_mb:.2f} MB)?', force_confirm=force):
                    for file_path in unused_files:
                        try:
                            if file_path.exists():
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                deleted_files += 1
                                deleted_size += file_size
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Не удалось удалить {file_path}: {e}'))
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'Удалено файлов: {deleted_files} ({deleted_size / (1024 * 1024):.2f} MB)'
                    ))
                    return deleted_files
            else:
                # Показываем первые 10 файлов
                for file_path in unused_files[:10]:
                    self.stdout.write(f'  - {file_path.relative_to(media_path)}')
                if count > 10:
                    self.stdout.write(f'  ... и еще {count - 10} файлов')
                return count
        else:
            self.stdout.write('Неиспользуемых файлов не найдено')
            return 0

    def confirm(self, message, force_confirm=False):
        """Запрашивает подтверждение у пользователя"""
        if force_confirm:
            return True

        response = input(f'{message} (yes/no): ')
        return response.lower() in ['yes', 'y', 'да', 'д']

    def print_stats(self, stats, dry_run):
        """Выводит статистику очистки"""
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING('СТАТИСТИКА (РЕЖИМ ПРОСМОТРА)'))
        else:
            self.stdout.write(self.style.SUCCESS('СТАТИСТИКА ОЧИСТКИ'))
        self.stdout.write('=' * 50)
        
        total = 0
        for key, value in stats.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    self.stdout.write(f'{key}.{sub_key}: {sub_value}')
                    total += sub_value
            else:
                self.stdout.write(f'{key}: {value}')
                total += value
        
        self.stdout.write('-' * 50)
        self.stdout.write(f'Всего записей: {total}')
        self.stdout.write('=' * 50)

