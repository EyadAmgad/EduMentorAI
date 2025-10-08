"""
Test configuration and utilities for EduMentorAI
"""
import os
import tempfile
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile


# Test database configuration
TEST_DATABASE_CONFIG = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Test media root for file uploads
TEST_MEDIA_ROOT = tempfile.mkdtemp()

# Test settings override
class BaseTestCase:
    """Base test case with common test configuration"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test configuration"""
        from django.test import override_settings
        cls.settings_override = override_settings(
            DATABASES=TEST_DATABASE_CONFIG,
            MEDIA_ROOT=TEST_MEDIA_ROOT,
            USE_SQLITE=True,
            CELERY_TASK_ALWAYS_EAGER=True,  # Run tasks synchronously in tests
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            CACHES={
                'default': {
                    'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
                }
            }
        )
        cls.settings_override.enable()
        super().setUpClass()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test configuration"""
        cls.settings_override.disable()
        super().tearDownClass()


class TestFileFactory:
    """Factory for creating test files"""
    
    @staticmethod
    def create_pdf_file(filename="test.pdf", content=None):
        """Create a mock PDF file for testing"""
        if content is None:
            content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF'
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type="application/pdf"
        )
    
    @staticmethod
    def create_txt_file(filename="test.txt", content=None):
        """Create a text file for testing"""
        if content is None:
            content = "This is test content for the text file."
        
        return SimpleUploadedFile(
            filename,
            content.encode('utf-8'),
            content_type="text/plain"
        )
    
    @staticmethod
    def create_docx_file(filename="test.docx"):
        """Create a mock DOCX file for testing"""
        # Mock DOCX content (simplified)
        content = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'  # ZIP file header
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    @staticmethod
    def create_pptx_file(filename="test.pptx"):
        """Create a mock PPTX file for testing"""
        # Mock PPTX content (simplified)
        content = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'  # ZIP file header
        
        return SimpleUploadedFile(
            filename,
            content,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )


class MockDataFactory:
    """Factory for creating mock data for tests"""
    
    @staticmethod
    def create_mock_embedding(dimension=384):
        """Create a mock embedding vector"""
        import random
        return [random.uniform(-1, 1) for _ in range(dimension)]
    
    @staticmethod
    def create_mock_chat_response():
        """Create a mock chat response"""
        return {
            'response': 'This is a mock response from the AI assistant.',
            'confidence': 0.85,
            'sources': ['chunk_1', 'chunk_2']
        }
    
    @staticmethod
    def create_mock_quiz_questions():
        """Create mock quiz questions"""
        return [
            {
                'question': 'What is Python?',
                'type': 'multiple_choice',
                'choices': [
                    {'text': 'A programming language', 'correct': True},
                    {'text': 'A snake', 'correct': False},
                    {'text': 'A web browser', 'correct': False},
                    {'text': 'A database', 'correct': False}
                ],
                'explanation': 'Python is a high-level programming language.'
            },
            {
                'question': 'Python is object-oriented.',
                'type': 'true_false',
                'answer': True,
                'explanation': 'Python supports object-oriented programming.'
            }
        ]


# Test decorators
def skip_if_no_external_services(test_func):
    """Skip test if external services are not available"""
    import pytest
    from django.conf import settings
    
    if not getattr(settings, 'EXTERNAL_SERVICES_AVAILABLE', False):
        return pytest.mark.skip(reason="External services not available")(test_func)
    return test_func


def slow_test(test_func):
    """Mark test as slow"""
    import pytest
    return pytest.mark.slow(test_func)


def integration_test(test_func):
    """Mark test as integration test"""
    import pytest
    return pytest.mark.integration(test_func)


# Test utilities
class DatabaseTestMixin:
    """Mixin for database-related test utilities"""
    
    def assert_model_count(self, model_class, expected_count):
        """Assert that a model has the expected count"""
        actual_count = model_class.objects.count()
        assert actual_count == expected_count, f"Expected {expected_count} {model_class.__name__} objects, got {actual_count}"
    
    def assert_model_exists(self, model_class, **kwargs):
        """Assert that a model instance exists with given criteria"""
        exists = model_class.objects.filter(**kwargs).exists()
        assert exists, f"{model_class.__name__} with criteria {kwargs} does not exist"
    
    def assert_model_does_not_exist(self, model_class, **kwargs):
        """Assert that a model instance does not exist with given criteria"""
        exists = model_class.objects.filter(**kwargs).exists()
        assert not exists, f"{model_class.__name__} with criteria {kwargs} should not exist"


class APITestMixin:
    """Mixin for API testing utilities"""
    
    def assert_json_response(self, response, expected_status=200):
        """Assert that response is JSON with expected status"""
        assert response.status_code == expected_status
        assert response['Content-Type'] == 'application/json'
        return response.json()
    
    def assert_error_response(self, response, expected_status=400):
        """Assert that response is an error with expected status"""
        assert response.status_code == expected_status
        if hasattr(response, 'json'):
            data = response.json()
            assert 'error' in data or 'errors' in data


class FileTestMixin:
    """Mixin for file-related test utilities"""
    
    def create_temp_file(self, content="", suffix=".txt"):
        """Create a temporary file for testing"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    def cleanup_temp_file(self, filepath):
        """Clean up a temporary file"""
        try:
            os.unlink(filepath)
        except OSError:
            pass
