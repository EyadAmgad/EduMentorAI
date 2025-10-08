"""
EduMentorAI Test Suite

This file imports all test modules to ensure they are discovered by Django's test runner.
Run tests with: python manage.py test
"""

# Import all test modules
from .tests.test_models import *
from .tests.test_forms import *
from .tests.test_views import *
from .tests.test_pipeline import *
from .tests.test_utils import *
from .tests.test_integration import *
