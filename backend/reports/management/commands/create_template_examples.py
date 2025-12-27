"""
Management command to create example report templates.

Usage:
    python manage.py create_template_examples
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from reports.models import ReportTemplate
from reports.fixtures.template_examples import create_example_templates

User = get_user_model()


class Command(BaseCommand):
    """Create example report templates for different report types."""

    help = 'Create example report templates for testing and documentation'

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing templates and recreate them',
        )
        parser.add_argument(
            '--user',
            type=int,
            help='User ID to assign as template creator',
        )

    def handle(self, *args, **options):
        """Execute command."""
        # Find admin user
        admin_user = None

        if options.get('user'):
            try:
                admin_user = User.objects.get(id=options['user'])
            except User.DoesNotExist:
                raise CommandError(f"User with ID {options['user']} not found")
        else:
            # Try to find an admin user
            admin_user = User.objects.filter(role='admin').first()
            if not admin_user:
                admin_user = User.objects.filter(is_superuser=True).first()

        if not admin_user:
            raise CommandError(
                "No admin user found. Please specify --user or create an admin user first."
            )

        self.stdout.write(f"Using user: {admin_user.get_full_name()} ({admin_user.email})")

        # Reset if requested
        if options.get('reset'):
            count = ReportTemplate.objects.count()
            ReportTemplate.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {count} existing templates")
            )

        # Create templates
        try:
            templates = create_example_templates(admin_user=admin_user)

            self.stdout.write(
                self.style.SUCCESS("\nSuccessfully created example templates:")
            )

            for name, template in templates.items():
                self.stdout.write(
                    f"  - {template.name} ({template.type})"
                    f" - ID: {template.id}"
                )

            self.stdout.write(
                self.style.SUCCESS("\nTemplates are ready to use!")
            )

        except Exception as e:
            raise CommandError(f"Error creating templates: {str(e)}")
