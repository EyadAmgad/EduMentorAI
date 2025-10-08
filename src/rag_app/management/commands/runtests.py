"""
Django management command for running tests with various options.

Usage:
    python manage.py runtests [options]
    python manage.py runtests --type unit
    python manage.py runtests --coverage
    python manage.py runtests --fast
"""

import os
import sys
import subprocess
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Run tests with various options and configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            choices=['all', 'unit', 'integration', 'models', 'views', 'forms', 'pipeline'],
            default='all',
            help='Type of tests to run (default: all)'
        )
        parser.add_argument(
            '--coverage',
            action='store_true',
            help='Run tests with coverage report'
        )
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Run only fast tests (exclude slow tests)'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Run tests with verbose output'
        )
        parser.add_argument(
            '--failfast',
            action='store_true',
            help='Stop on first test failure'
        )
        parser.add_argument(
            '--parallel',
            action='store_true',
            help='Run tests in parallel'
        )
        parser.add_argument(
            '--keepdb',
            action='store_true',
            help='Keep test database between runs'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode for tests'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(
            self.style.SUCCESS('🧪 Running EduMentorAI Tests')
        )
        
        # Check if pytest is available
        try:
            import pytest
            use_pytest = True
        except ImportError:
            self.stdout.write(
                self.style.WARNING('Pytest not found, using Django test runner')
            )
            use_pytest = False
        
        if use_pytest and not options.get('debug'):
            success = self._run_pytest_tests(options)
        else:
            success = self._run_django_tests(options)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS('\n✅ All tests passed!')
            )
        else:
            self.stdout.write(
                self.style.ERROR('\n❌ Some tests failed!')
            )
            sys.exit(1)

    def _run_pytest_tests(self, options):
        """Run tests using pytest"""
        cmd = ['python', '-m', 'pytest']
        
        # Add test directory
        test_type = options['type']
        if test_type == 'all':
            cmd.append('rag_app/tests/')
        elif test_type == 'unit':
            cmd.extend(['rag_app/tests/', '-m', 'not integration'])
        elif test_type == 'integration':
            cmd.append('rag_app/tests/test_integration.py')
        elif test_type == 'models':
            cmd.append('rag_app/tests/test_models.py')
        elif test_type == 'views':
            cmd.append('rag_app/tests/test_views.py')
        elif test_type == 'forms':
            cmd.append('rag_app/tests/test_forms.py')
        elif test_type == 'pipeline':
            cmd.append('rag_app/tests/test_pipeline.py')
        
        # Add coverage options
        if options['coverage']:
            cmd.extend([
                '--cov=rag_app',
                '--cov-report=html',
                '--cov-report=term-missing'
            ])
        
        # Add fast option
        if options['fast']:
            cmd.extend(['-m', 'not slow'])
        
        # Add verbose option
        if options['verbose']:
            cmd.append('-v')
        
        # Add failfast option
        if options['failfast']:
            cmd.append('-x')
        
        # Add parallel option
        if options['parallel']:
            cmd.extend(['-n', 'auto'])
        
        self.stdout.write(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode == 0
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running pytest: {e}')
            )
            return False

    def _run_django_tests(self, options):
        """Run tests using Django's test runner"""
        from django.core.management import call_command
        from django.test.utils import get_runner
        from django.conf import settings
        
        # Prepare test runner options
        test_options = {}
        
        if options['verbose']:
            test_options['verbosity'] = 2
        
        if options['failfast']:
            test_options['failfast'] = True
        
        if options['parallel']:
            test_options['parallel'] = True
        
        if options['keepdb']:
            test_options['keepdb'] = True
        
        if options['debug']:
            test_options['debug_mode'] = True
        
        # Determine test labels based on type
        test_type = options['type']
        if test_type == 'all':
            test_labels = ['rag_app.tests']
        elif test_type == 'unit':
            test_labels = [
                'rag_app.tests.test_models',
                'rag_app.tests.test_forms',
                'rag_app.tests.test_utils',
            ]
        elif test_type == 'integration':
            test_labels = ['rag_app.tests.test_integration']
        elif test_type == 'models':
            test_labels = ['rag_app.tests.test_models']
        elif test_type == 'views':
            test_labels = ['rag_app.tests.test_views']
        elif test_type == 'forms':
            test_labels = ['rag_app.tests.test_forms']
        elif test_type == 'pipeline':
            test_labels = ['rag_app.tests.test_pipeline']
        
        try:
            call_command('test', *test_labels, **test_options)
            return True
        except SystemExit as e:
            return e.code == 0
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running Django tests: {e}')
            )
            return False

    def _print_usage_help(self):
        """Print usage examples"""
        self.stdout.write(
            self.style.HTTP_INFO('\n📋 Usage Examples:')
        )
        examples = [
            'python manage.py runtests',
            'python manage.py runtests --type unit',
            'python manage.py runtests --type integration',
            'python manage.py runtests --coverage',
            'python manage.py runtests --fast',
            'python manage.py runtests --verbose --failfast',
            'python manage.py runtests --type models --coverage',
        ]
        
        for example in examples:
            self.stdout.write(f'  {example}')
