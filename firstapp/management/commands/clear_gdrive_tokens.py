#!/usr/bin/env python
"""
Clear all Google Drive OAuth tokens to force re-authentication
Run this after changing API scopes to read-only
"""

import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Clear all Google Drive OAuth tokens to force re-authentication with read-only permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to clear all tokens',
        )

    def handle(self, *args, **options):
        tokens_dir = os.path.join(settings.BASE_DIR, 'gdrive_tokens')
        
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will clear all Google Drive authentication tokens.\n'
                    'Users will need to re-authenticate with read-only permissions.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return

        try:
            if os.path.exists(tokens_dir):
                # Count files before deletion
                token_files = [f for f in os.listdir(tokens_dir) if f.endswith('.pickle')]
                file_count = len(token_files)
                
                # Remove all token files
                shutil.rmtree(tokens_dir)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Cleared {file_count} Google Drive authentication tokens.\n'
                        f'Users will need to re-authenticate with read-only permissions.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No Google Drive tokens directory found.')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error clearing tokens: {e}')
            )