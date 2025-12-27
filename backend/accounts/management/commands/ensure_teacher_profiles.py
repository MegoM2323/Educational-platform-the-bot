"""
Management command to ensure all teacher users have TeacherProfile records
"""
from django.core.management.base import BaseCommand
from accounts.models import User, TeacherProfile


class Command(BaseCommand):
    help = 'Ensure all teacher users have TeacherProfile records with default values'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing profiles with default values if fields are empty',
        )

    def handle(self, *args, **options):
        update_existing = options['update_existing']
        
        # Find all teacher users
        teachers = User.objects.filter(role='teacher')
        total_teachers = teachers.count()
        
        self.stdout.write(f'Found {total_teachers} teacher users')
        
        created_count = 0
        updated_count = 0
        
        for teacher in teachers:
            # Check if profile exists
            profile, created = TeacherProfile.objects.get_or_create(
                user=teacher,
                defaults={
                    'bio': 'Опытный преподаватель платформы THE BOT',
                    'subject': 'Математика',
                    'experience_years': 3,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created TeacherProfile for {teacher.email}')
                )
            elif update_existing:
                # Update empty fields
                needs_update = False
                
                if not profile.bio:
                    profile.bio = 'Опытный преподаватель платформы THE BOT'
                    needs_update = True
                
                if not profile.subject:
                    profile.subject = 'Математика'
                    needs_update = True
                
                if profile.experience_years == 0:
                    profile.experience_years = 3
                    needs_update = True
                
                if needs_update:
                    profile.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Updated TeacherProfile for {teacher.email}')
                    )
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n📊 Summary:'))
        self.stdout.write(f'   Total teachers: {total_teachers}')
        self.stdout.write(f'   Profiles created: {created_count}')
        if update_existing:
            self.stdout.write(f'   Profiles updated: {updated_count}')
        
        self.stdout.write(self.style.SUCCESS('\n✅ All teacher users have TeacherProfile records'))
