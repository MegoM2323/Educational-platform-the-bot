"""
Management command to fix missing ChatParticipant records.

This command creates ChatParticipant records for all ChatRoom participants
who are in the M2M participants relation but don't have a ChatParticipant record.

Usage:
    python manage.py fix_chat_participants
    python manage.py fix_chat_participants --dry-run
"""

from django.core.management.base import BaseCommand
from chat.models import ChatRoom, ChatParticipant


class Command(BaseCommand):
    help = 'Create missing ChatParticipant records for existing chat room participants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no changes will be made'))

        total_created = 0
        total_rooms = 0
        errors = []

        # Get all active chat rooms
        chat_rooms = ChatRoom.objects.filter(is_active=True).prefetch_related('participants')

        for room in chat_rooms:
            total_rooms += 1
            room_created = 0

            for user in room.participants.all():
                # Check if ChatParticipant exists
                exists = ChatParticipant.objects.filter(room=room, user=user).exists()

                if not exists:
                    if not dry_run:
                        try:
                            ChatParticipant.objects.create(room=room, user=user)
                            room_created += 1
                            total_created += 1
                        except Exception as e:
                            errors.append(f"Error creating ChatParticipant for room {room.id}, user {user.id}: {e}")
                    else:
                        room_created += 1
                        total_created += 1

            if room_created > 0:
                self.stdout.write(
                    f"Room {room.id} ({room.name[:50]}...): "
                    f"{'would create' if dry_run else 'created'} {room_created} ChatParticipant(s)"
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f"Total rooms processed: {total_rooms}")
        self.stdout.write(
            f"ChatParticipant records {'to create' if dry_run else 'created'}: {total_created}"
        )

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:10]:  # Show first 10 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run and total_created > 0:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
