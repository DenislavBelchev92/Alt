"""
Reset Google Drive OAuth for a specific user
Usage: python manage.py reset_oauth --user-id <id>
"""

from django.core.management.base import BaseCommand, CommandError
from firstapp.gdrive import reset_user_oauth


class Command(BaseCommand):
    help = 'Reset Google Drive OAuth tokens for a specific user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            required=True,
            help='User ID to reset OAuth tokens for',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the reset operation',
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    f'This will clear Google Drive authentication for user {user_id}.\n'
                    f'The user will need to re-authenticate.\n'
                    f'Run with --confirm to proceed.'
                )
            )
            return

        try:
            success = reset_user_oauth(user_id)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully reset Google Drive OAuth for user {user_id}.\n'
                        f'User will need to re-authenticate on next access.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to reset OAuth for user {user_id}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error resetting OAuth: {e}')
            )