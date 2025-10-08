"""
Base test classes and utilities for RAG app tests.
"""
import uuid
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.db import transaction
from rag_app.models import Subject, Document, ChatSession


class BaseTestCase(TestCase):
    """Base test case with common setup and utilities."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        cls._test_counter = 0
    
    def setUp(self):
        """Set up test data with unique identifiers."""
        # Generate unique identifiers for this test
        test_id = str(uuid.uuid4())[:8]
        self.__class__._test_counter += 1
        
        # Create test user with unique username
        self.user = User.objects.create_user(
            username=f'testuser_{test_id}_{self._test_counter}',
            email=f'test_{test_id}@example.com',
            password='testpass123'
        )
        
        # Store unique identifiers for use in tests
        self.test_id = test_id
        self.test_counter = self._test_counter
    
    def create_subject(self, name=None, code=None, created_by=None):
        """Create a subject with unique code."""
        if name is None:
            name = f'Test Subject {self.test_id}'
        if code is None:
            code = f'TEST{self.test_counter}{self.test_id[:4].upper()}'
        if created_by is None:
            created_by = self.user
            
        return Subject.objects.create(
            name=name,
            code=code,
            created_by=created_by
        )
    
    def create_document(self, subject=None, title=None, uploaded_by=None):
        """Create a document with unique title."""
        if subject is None:
            subject = self.create_subject()
        if title is None:
            title = f'Test Document {self.test_id}'
        if uploaded_by is None:
            uploaded_by = self.user
            
        return Document.objects.create(
            title=title,
            subject=subject,
            uploaded_by=uploaded_by,
            file_size=1024
        )
    
    def create_chat_session(self, subject=None, document=None, created_by=None):
        """Create a chat session."""
        if created_by is None:
            created_by = self.user
            
        return ChatSession.objects.create(
            subject=subject,
            document=document,
            user=created_by
        )


class BaseTransactionTestCase(TransactionTestCase):
    """Base transaction test case for tests requiring database transactions."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class."""
        super().setUpClass()
        cls._test_counter = 0
    
    def setUp(self):
        """Set up test data with unique identifiers."""
        # Generate unique identifiers for this test
        test_id = str(uuid.uuid4())[:8]
        self.__class__._test_counter += 1
        
        # Create test user with unique username
        self.user = User.objects.create_user(
            username=f'testuser_{test_id}_{self._test_counter}',
            email=f'test_{test_id}@example.com',
            password='testpass123'
        )
        
        # Store unique identifiers for use in tests
        self.test_id = test_id
        self.test_counter = self._test_counter
    
    def create_subject(self, name=None, code=None, created_by=None):
        """Create a subject with unique code."""
        if name is None:
            name = f'Test Subject {self.test_id}'
        if code is None:
            code = f'TEST{self.test_counter}{self.test_id[:4].upper()}'
        if created_by is None:
            created_by = self.user
            
        return Subject.objects.create(
            name=name,
            code=code,
            created_by=created_by
        )
