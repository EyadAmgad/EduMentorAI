"""
Django management command for setting up the testing environment.

Usage:
    python manage.py setup_testing
"""

import os
import sys
import subprocess
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Set up the testing environment and install test dependencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-deps',
            action='store_true',
            help='Skip installing test dependencies'
        )
        parser.add_argument(
            '--create-superuser',
            action='store_true',
            help='Create a test superuser'
        )
        parser.add_argument(
            '--reset-db',
            action='store_true',
            help='Reset the test database'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(
            self.style.SUCCESS('🚀 Setting up EduMentorAI testing environment...')
        )
        
        # Install test dependencies
        if not options['skip_deps']:
            self._install_test_dependencies()
        
        # Run migrations
        self._run_migrations()
        
        # Create superuser if requested
        if options['create_superuser']:
            self._create_test_superuser()
        
        # Reset database if requested
        if options['reset_db']:
            self._reset_test_database()
        
        # Collect static files
        self._collect_static_files()
        
        # Run system checks
        self._run_system_checks()
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Testing environment setup complete!')
        )
        
        self._print_next_steps()

    def _install_test_dependencies(self):
        """Install test dependencies"""
        self.stdout.write('📦 Installing test dependencies...')
        
        test_packages = [
            'pytest>=7.0.0',
            'pytest-django>=4.5.0',
            'pytest-cov>=4.0.0',
            'pytest-xdist>=3.0.0',
            'factory-boy>=3.2.0',
            'coverage>=7.0.0',
            'mock>=4.0.0',
        ]
        
        for package in test_packages:
            try:
                subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package
                ], check=True, capture_output=True)
                self.stdout.write(f'  ✓ Installed {package}')
            except subprocess.CalledProcessError as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Failed to install {package}: {e}')
                )

    def _run_migrations(self):
        """Run database migrations"""
        self.stdout.write('🗄️ Running database migrations...')
        from django.core.management import call_command
        
        try:
            call_command('migrate', verbosity=0)
            self.stdout.write('  ✓ Migrations completed')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Migration failed: {e}')
            )

    def _create_test_superuser(self):
        """Create a test superuser"""
        self.stdout.write('👤 Creating test superuser...')
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        if not User.objects.filter(username='admin').exists():
            try:
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123'
                )
                self.stdout.write('  ✓ Test superuser created (admin/admin123)')
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Failed to create superuser: {e}')
                )
        else:
            self.stdout.write('  ✓ Test superuser already exists')

    def _reset_test_database(self):
        """Reset the test database"""
        self.stdout.write('🔄 Resetting test database...')
        from django.core.management import call_command
        
        try:
            # Flush the database
            call_command('flush', '--noinput', verbosity=0)
            
            # Run migrations again
            call_command('migrate', verbosity=0)
            
            self.stdout.write('  ✓ Database reset completed')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Database reset failed: {e}')
            )

    def _collect_static_files(self):
        """Collect static files"""
        self.stdout.write('📁 Collecting static files...')
        from django.core.management import call_command
        
        try:
            call_command('collectstatic', '--noinput', '--clear', verbosity=0)
            self.stdout.write('  ✓ Static files collected')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Static files collection failed: {e}')
            )

    def _run_system_checks(self):
        """Run Django system checks"""
        self.stdout.write('🔍 Running system checks...')
        from django.core.management import call_command
        
        try:
            call_command('check', verbosity=0)
            self.stdout.write('  ✓ System checks passed')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ System checks failed: {e}')
            )

    def _print_next_steps(self):
        """Print next steps for the user"""
        self.stdout.write(
            self.style.HTTP_INFO('\n📋 Next steps:')
        )
        
        steps = [
            'Run all tests: python manage.py runtests',
            'Run unit tests: python manage.py runtests --type unit',
            'Run with coverage: python manage.py runtests --coverage',
            'Run specific test file: python manage.py test rag_app.tests.test_models',
            'Generate coverage report: python manage.py test_coverage',
        ]
        
        for step in steps:
            self.stdout.write(f'  • {step}')
        
        self.stdout.write(
            self.style.HTTP_INFO('\n🔧 Available test commands:')
        )
        
        commands = [
            'python manage.py runtests --help',
            'python manage.py test_coverage --help',
            'python manage.py test --help',
        ]
        
        for command in commands:
            self.stdout.write(f'  • {command}')
