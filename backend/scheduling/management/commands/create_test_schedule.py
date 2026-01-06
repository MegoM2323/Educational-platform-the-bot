from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta, time

from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment, TeacherSubject

User = get_user_model()


class Command(BaseCommand):
    help = "Создаёт 10 тестовых уроков на следующую неделю для student@test.com и teacher@test.com"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("📅 СОЗДАНИЕ ТЕСТОВЫХ УРОКОВ"))
        self.stdout.write("="*80)

        # 1. Получаем/создаём пользователей
        teacher = User.objects.filter(email="teacher@test.com").first()
        if not teacher:
            self.stdout.write(
                self.style.ERROR("✗ Учитель teacher@test.com не найден. Сначала запустите create_test_users_all")
            )
            return
        self.stdout.write(f"✓ Найден учитель: {teacher.get_full_name()}")

        student = User.objects.filter(email="student@test.com").first()
        if not student:
            self.stdout.write(
                self.style.ERROR("✗ Студент student@test.com не найден. Сначала запустите create_test_users_all")
            )
            return
        self.stdout.write(f"✓ Найден студент: {student.get_full_name()}")

        # 2. Получаем/создаём предмет
        subject, created = Subject.objects.get_or_create(
            name="Математика",
            defaults={"description": "Тестовый курс математики", "color": "#3B82F6"}
        )
        if created:
            self.stdout.write(f"✓ Создан предмет: {subject.name}")
        else:
            self.stdout.write(f"✓ Найден предмет: {subject.name}")

        # 3. Создаём связь teacher -> subject (если её нет)
        teacher_subject, created = TeacherSubject.objects.get_or_create(
            teacher=teacher,
            subject=subject,
            defaults={"is_active": True}
        )
        if created:
            self.stdout.write(f"✓ Создана связь учитель-предмет")
        else:
            self.stdout.write(f"✓ Найдена связь учитель-предмет")

        # 4. Создаём enrollment (student -> subject -> teacher)
        enrollment, created = SubjectEnrollment.objects.get_or_create(
            student=student,
            subject=subject,
            teacher=teacher,
            defaults={"is_active": True, "assigned_by": teacher}
        )
        if created:
            self.stdout.write(f"✓ Создено зачисление студента на предмет")
        else:
            self.stdout.write(f"✓ Найдено зачисление студента на предмет")

        # 5. Определяем дату начала (следующий понедельник)
        now = timezone.now()
        current_weekday = now.weekday()

        if current_weekday == 0:
            if now.hour >= 18:
                days_until_monday = 7
            else:
                days_until_monday = 7
        else:
            days_until_monday = (7 - current_weekday) % 7

        start_date = (now + timedelta(days=days_until_monday)).date()

        # 6. Конфигурация уроков: 10 уроков, 2 в день с пн по пт
        lesson_configs = [
            # Понедельник
            {"day_offset": 0, "start_time": time(9, 0), "lesson_type": "REGULAR", "notes": "Утренний урок (пн)"},
            {"day_offset": 0, "start_time": time(13, 0), "lesson_type": "CONSULTATION", "notes": "Дневная консультация (пн)"},
            # Вторник
            {"day_offset": 1, "start_time": time(9, 0), "lesson_type": "REGULAR", "notes": "Утренний урок (вт)"},
            {"day_offset": 1, "start_time": time(17, 0), "lesson_type": "EXAM_PREP", "notes": "Вечерняя подготовка к экзамену (вт)"},
            # Среда
            {"day_offset": 2, "start_time": time(13, 0), "lesson_type": "REGULAR", "notes": "Дневной урок (ср)"},
            {"day_offset": 2, "start_time": time(17, 0), "lesson_type": "CONSULTATION", "notes": "Вечерняя консультация (ср)"},
            # Четверг
            {"day_offset": 3, "start_time": time(9, 0), "lesson_type": "EXAM_PREP", "notes": "Утренняя подготовка к экзамену (чт)"},
            {"day_offset": 3, "start_time": time(13, 0), "lesson_type": "REGULAR", "notes": "Дневной урок (чт)"},
            # Пятница
            {"day_offset": 4, "start_time": time(9, 0), "lesson_type": "CONSULTATION", "notes": "Утренняя консультация (пт)"},
            {"day_offset": 4, "start_time": time(17, 0), "lesson_type": "REGULAR", "notes": "Вечерний итоговый урок (пт)"},
        ]

        # 7. Создаём уроки
        created_lessons = []
        self.stdout.write("\n" + "-"*80)
        self.stdout.write(self.style.WARNING("📚 СОЗДАНИЕ УРОКОВ:"))
        self.stdout.write("-"*80)

        for idx, config in enumerate(lesson_configs, 1):
            lesson_date = start_date + timedelta(days=config["day_offset"])
            start_time = config["start_time"]
            end_time = (
                timezone.datetime.combine(lesson_date, start_time) + timedelta(hours=2)
            ).time()

            if not enrollment:
                self.stdout.write(
                    self.style.ERROR(
                        f"⚠️  [{idx:2d}] ПРОПУЩЕН (нет зачисления): {lesson_date} {start_time}-{end_time}"
                    )
                )
                continue

            overlapping = Lesson.objects.filter(
                date=lesson_date,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).filter(
                models.Q(teacher=teacher) | models.Q(student=student)
            )

            if overlapping.exists():
                conflict_lesson = overlapping.first()
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  [{idx:2d}] КОНФЛИКТ ВРЕМЕНИ: {lesson_date} {start_time}-{end_time} "
                        f"пересекается с {conflict_lesson.start_time}-{conflict_lesson.end_time}"
                    )
                )
                continue

            lesson, created = Lesson.objects.get_or_create(
                teacher=teacher,
                student=student,
                subject=subject,
                date=lesson_date,
                start_time=start_time,
                defaults={
                    "end_time": end_time,
                    "notes": config["notes"],
                    "description": f"{config['lesson_type']} - {config['notes']}",
                    "status": Lesson.Status.CONFIRMED,
                }
            )

            if created:
                created_lessons.append(lesson)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ [{idx:2d}] Создан урок: {lesson_date} {start_time}-{end_time} "
                        f"({config['lesson_type']})"
                    )
                )
            else:
                self.stdout.write(
                    f"♻️  [{idx:2d}] Урок уже существует: {lesson_date} {start_time}-{end_time}"
                )

        # 8. Вывод итоговой статистики
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS(f"✅ ИТОГО СОЗДАНО УРОКОВ: {len(created_lessons)}"))
        self.stdout.write("="*80)

        if created_lessons:
            self.stdout.write("\n📋 РАСПИСАНИЕ:")
            self.stdout.write("-"*80)
            for lesson in sorted(created_lessons, key=lambda x: (x.date, x.start_time)):
                day_name = lesson.date.strftime("%A")
                date_str = lesson.date.strftime("%d.%m.%Y")
                self.stdout.write(
                    f"   {day_name:10} {date_str} | "
                    f"{lesson.start_time.strftime('%H:%M')}-{lesson.end_time.strftime('%H:%M')} | "
                    f"{lesson.notes}"
                )

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ ТЕСТОВЫЕ УРОКИ ГОТОВЫ!"))
        self.stdout.write("="*80)
        self.stdout.write(f"\n👨‍🏫 Учитель: {teacher.get_full_name()} ({teacher.email})")
        self.stdout.write(f"👨‍🎓 Студент: {student.get_full_name()} ({student.email})")
        self.stdout.write(f"📖 Предмет: {subject.name}")
        self.stdout.write(f"\n🗓️  Первый урок: {created_lessons[0].date.strftime('%d.%m.%Y %H:%M') if created_lessons else 'нет'}")
        self.stdout.write("="*80 + "\n")
