"""
Management command for exporting user data (GDPR compliance).

Usage:
    python manage.py export_user_data --user_id=123 --format=json --output=/tmp/
    python manage.py export_user_data --user_id=123 --format=csv
"""
import json
import os
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from accounts.export import UserDataExporter, ExportFileManager

User = get_user_model()


class Command(BaseCommand):
    """
    Export user data to JSON or CSV format.
    """

    help = 'Export user data in GDPR-compliant format (JSON or CSV)'

    def add_arguments(self, parser):
        """
        Define command line arguments.
        """
        parser.add_argument(
            '--user_id',
            type=int,
            required=True,
            help='ID of user to export'
        )

        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv'],
            default='json',
            help='Export format (json or csv)'
        )

        parser.add_argument(
            '--output',
            type=str,
            default='.',
            help='Output directory (default: current directory)'
        )

    def handle(self, *args, **options):
        """
        Execute the export command.
        """
        user_id = options['user_id']
        export_format = options['format']
        output_dir = options['output']

        # Validate user exists
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise CommandError(f'User with ID {user_id} not found')

        # Validate output directory
        output_path = Path(output_dir)
        if not output_path.exists():
            raise CommandError(f'Output directory {output_dir} does not exist')

        if not output_path.is_dir():
            raise CommandError(f'{output_dir} is not a directory')

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting export for user: {user.get_full_name()} ({user.email})'
            )
        )

        try:
            # Collect data
            exporter = UserDataExporter(user)
            exporter.collect_all_data()

            if export_format == 'json':
                self._export_json(user_id, exporter, output_path)
            else:
                self._export_csv(user_id, exporter, output_path)

            self.stdout.write(
                self.style.SUCCESS('Export completed successfully!')
            )

        except Exception as e:
            raise CommandError(f'Export failed: {str(e)}')

    def _export_json(self, user_id: int, exporter: UserDataExporter, output_path: Path):
        """
        Export data as JSON file.

        Args:
            user_id: User ID
            exporter: UserDataExporter instance
            output_path: Output directory path
        """
        # Generate filename
        timestamp = exporter.export_data['export_timestamp'].split('T')[0]
        filename = f'export_user_{user_id}_{timestamp}.json'
        file_path = output_path / filename

        # Write JSON file
        json_content = exporter.to_json()
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(json_content)

        file_size = file_path.stat().st_size
        self.stdout.write(
            f'JSON export saved: {file_path}'
        )
        self.stdout.write(
            f'File size: {file_size:,} bytes'
        )

    def _export_csv(self, user_id: int, exporter: UserDataExporter, output_path: Path):
        """
        Export data as multiple CSV files in a directory.

        Args:
            user_id: User ID
            exporter: UserDataExporter instance
            output_path: Output directory path
        """
        import zipfile

        csv_files = exporter.to_csv()

        # Create directory for CSV files
        timestamp = exporter.export_data['export_timestamp'].split('T')[0]
        csv_dir = output_path / f'export_user_{user_id}_{timestamp}'
        csv_dir.mkdir(exist_ok=True)

        # Write CSV files
        file_count = 0
        total_size = 0
        for filename, content in csv_files.items():
            file_path = csv_dir / filename
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            file_count += 1
            total_size += file_path.stat().st_size
            self.stdout.write(f'  - {filename}')

        # Create ZIP archive
        zip_filename = f'export_user_{user_id}_{timestamp}.zip'
        zip_path = output_path / zip_filename

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in csv_dir.iterdir():
                zipf.write(file_path, arcname=file_path.name)

        # Clean up CSV directory
        for file_path in csv_dir.iterdir():
            file_path.unlink()
        csv_dir.rmdir()

        zip_size = zip_path.stat().st_size
        self.stdout.write(
            f'CSV export saved: {zip_path}'
        )
        self.stdout.write(
            f'Files included: {file_count}'
        )
        self.stdout.write(
            f'ZIP size: {zip_size:,} bytes'
        )
