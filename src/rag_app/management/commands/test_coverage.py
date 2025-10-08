"""
Django management command for generating test coverage reports.

Usage:
    python manage.py test_coverage
    python manage.py test_coverage --format html
    python manage.py test_coverage --open
"""

import os
import sys
import subprocess
import webbrowser
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Generate and view test coverage reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['html', 'xml', 'json', 'term'],
            default='html',
            help='Coverage report format (default: html)'
        )
        parser.add_argument(
            '--open',
            action='store_true',
            help='Open HTML coverage report in browser'
        )
        parser.add_argument(
            '--include',
            type=str,
            help='Include only specific modules (comma-separated)'
        )
        parser.add_argument(
            '--exclude',
            type=str,
            help='Exclude specific modules (comma-separated)'
        )
        parser.add_argument(
            '--min-coverage',
            type=int,
            default=80,
            help='Minimum coverage percentage (default: 80)'
        )
        parser.add_argument(
            '--fail-under',
            action='store_true',
            help='Fail if coverage is below minimum'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(
            self.style.SUCCESS('📊 Generating test coverage report...')
        )
        
        # Check if coverage tools are available
        if not self._check_coverage_tools():
            return
        
        # Run tests with coverage
        success = self._run_coverage_tests(options)
        
        if not success:
            self.stdout.write(
                self.style.ERROR('❌ Tests failed, coverage report may be incomplete')
            )
        
        # Generate coverage reports
        self._generate_reports(options)
        
        # Check coverage threshold
        if options['fail_under']:
            self._check_coverage_threshold(options['min_coverage'])
        
        # Open report if requested
        if options['open'] and options['format'] == 'html':
            self._open_html_report()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Coverage report generation complete!')
        )

    def _check_coverage_tools(self):
        """Check if coverage tools are available"""
        try:
            import coverage
            return True
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Coverage package not found. Install with: pip install coverage'
                )
            )
            return False

    def _run_coverage_tests(self, options):
        """Run tests with coverage collection"""
        self.stdout.write('🧪 Running tests with coverage...')
        
        # Prepare coverage command
        cmd = ['python', '-m', 'coverage', 'run']
        
        # Add source option
        cmd.extend(['--source', 'rag_app'])
        
        # Add include/exclude options
        if options['include']:
            modules = options['include'].split(',')
            for module in modules:
                cmd.extend(['--include', f'*{module.strip()}*'])
        
        if options['exclude']:
            modules = options['exclude'].split(',')
            for module in modules:
                cmd.extend(['--omit', f'*{module.strip()}*'])
        
        # Add Django test command
        cmd.extend(['manage.py', 'test', 'rag_app.tests'])
        
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.stdout.write('  ✓ Tests completed successfully')
                return True
            else:
                self.stdout.write(
                    self.style.WARNING('  ⚠ Some tests failed')
                )
                if result.stderr:
                    self.stdout.write(result.stderr)
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error running coverage tests: {e}')
            )
            return False

    def _generate_reports(self, options):
        """Generate coverage reports in requested formats"""
        report_format = options['format']
        
        if report_format == 'html':
            self._generate_html_report()
        elif report_format == 'xml':
            self._generate_xml_report()
        elif report_format == 'json':
            self._generate_json_report()
        elif report_format == 'term':
            self._generate_terminal_report()

    def _generate_html_report(self):
        """Generate HTML coverage report"""
        self.stdout.write('📄 Generating HTML coverage report...')
        
        try:
            cmd = ['python', '-m', 'coverage', 'html', '--directory=htmlcov']
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            self.stdout.write('  ✓ HTML report generated in htmlcov/')
            self.stdout.write('  📂 Open htmlcov/index.html to view the report')
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate HTML report: {e}')
            )

    def _generate_xml_report(self):
        """Generate XML coverage report"""
        self.stdout.write('📄 Generating XML coverage report...')
        
        try:
            cmd = ['python', '-m', 'coverage', 'xml']
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            self.stdout.write('  ✓ XML report generated as coverage.xml')
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate XML report: {e}')
            )

    def _generate_json_report(self):
        """Generate JSON coverage report"""
        self.stdout.write('📄 Generating JSON coverage report...')
        
        try:
            cmd = ['python', '-m', 'coverage', 'json']
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            self.stdout.write('  ✓ JSON report generated as coverage.json')
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate JSON report: {e}')
            )

    def _generate_terminal_report(self):
        """Generate terminal coverage report"""
        self.stdout.write('📄 Generating terminal coverage report...')
        
        try:
            cmd = ['python', '-m', 'coverage', 'report', '--show-missing']
            result = subprocess.run(cmd, check=False, text=True)
            
            if result.returncode == 0:
                self.stdout.write('  ✓ Terminal report displayed above')
            else:
                self.stdout.write('  ⚠ Terminal report generated with warnings')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to generate terminal report: {e}')
            )

    def _check_coverage_threshold(self, min_coverage):
        """Check if coverage meets minimum threshold"""
        self.stdout.write(f'📊 Checking coverage threshold ({min_coverage}%)...')
        
        try:
            cmd = ['python', '-m', 'coverage', 'report', '--fail-under', str(min_coverage)]
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Coverage meets minimum threshold ({min_coverage}%)')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ Coverage below minimum threshold ({min_coverage}%)')
                )
                sys.exit(1)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error checking coverage threshold: {e}')
            )

    def _open_html_report(self):
        """Open HTML coverage report in browser"""
        html_file = os.path.join(os.getcwd(), 'htmlcov', 'index.html')
        
        if os.path.exists(html_file):
            try:
                webbrowser.open(f'file://{html_file}')
                self.stdout.write('  🌐 Opening coverage report in browser...')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠ Could not open browser: {e}')
                )
        else:
            self.stdout.write(
                self.style.ERROR('  ❌ HTML coverage report not found')
            )
