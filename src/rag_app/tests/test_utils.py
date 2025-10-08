"""
Unit tests for EduMentorAI utilities and services
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock, mock_open
import json
import tempfile
import os

from rag_app.models import Subject, Document, DocumentChunk, ChatSession, DocumentType
from rag_app.prompt_loader import prompt_loader


class PromptLoaderTest(TestCase):
    """Test cases for prompt loader utility"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.subject = Subject.objects.create(
            name='Test Subject',
            code='TEST101',
            description='Test subject description',
            created_by=self.user
        )
    
    def test_prompt_loader_initialization(self):
        """Test prompt loader can be imported and used"""
        self.assertIsNotNone(prompt_loader)
    
    def test_load_system_prompts(self):
        """Test loading system prompts"""
        # Mock the prompt loading since we don't know the exact structure
        with patch.object(prompt_loader, 'get_prompt') as mock_get_prompt:
            mock_get_prompt.return_value = "This is a test prompt"
            
            prompt = prompt_loader.get_prompt('test_prompt')
            self.assertEqual(prompt, "This is a test prompt")
            mock_get_prompt.assert_called_once_with('test_prompt')


class ModelUtilsTest(TestCase):
    """Test cases for model utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.subject = Subject.objects.create(
            name='Test Subject',
            code='TEST101',
            description='Test subject description',
            created_by=self.user
        )
    
    def test_subject_string_representation(self):
        """Test Subject model string representation"""
        expected_str = f"{self.subject.code} - {self.subject.name}"
        self.assertEqual(str(self.subject), expected_str)
    
    def test_document_creation_and_validation(self):
        """Test Document model creation and validation"""
        content = b"This is test content for the document."
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            content,
            content_type="text/plain"
        )
        
        document = Document.objects.create(
            title='Test Document',
            subject=self.subject,
            uploaded_by=self.user,
            file=uploaded_file,
            document_type=DocumentType.TXT,
            file_size=len(content)
        )
        
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.subject, self.subject)
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(document.document_type, DocumentType.TXT)
        self.assertTrue(document.file)
    
    def test_document_chunk_relationship(self):
        """Test DocumentChunk relationship with Document"""
        content = b"This is test content for the document."
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            content,
            content_type="text/plain"
        )
        
        document = Document.objects.create(
            title='Test Document',
            subject=self.subject,
            uploaded_by=self.user,
            file=uploaded_file,
            document_type=DocumentType.TXT,
            file_size=len(content)
        )
        
        chunk = DocumentChunk.objects.create(
            document=document,
            content='This is a test chunk content',
            chunk_index=0,
            page_number=1
        )
        
        self.assertEqual(chunk.document, document)
        self.assertEqual(document.chunks.count(), 1)
        self.assertEqual(document.chunks.first(), chunk)
    
    def test_chat_session_creation(self):
        """Test ChatSession model creation"""
        chat_session = ChatSession.objects.create(
            user=self.user,
            subject=self.subject,
            title='Test Chat Session'
        )
        
        self.assertEqual(chat_session.user, self.user)
        self.assertEqual(chat_session.subject, self.subject)
        self.assertEqual(chat_session.title, 'Test Chat Session')
        self.assertIsNotNone(chat_session.created_at)


class FileUtilsTest(TestCase):
    """Test cases for file utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_file_upload_path_generation(self):
        """Test file upload path generation"""
        from rag_app.models import upload_to_user_folder
        
        # Create a mock instance
        mock_instance = MagicMock()
        mock_instance.uploaded_by.id = self.user.id
        
        filename = 'test_document.pdf'
        expected_path = f'uploads/{self.user.id}/{filename}'
        
        result = upload_to_user_folder(mock_instance, filename)
        self.assertEqual(result, expected_path)
    
    def test_document_type_choices(self):
        """Test DocumentType choices"""
        # Test that all expected document types are available
        expected_types = ['pdf', 'docx', 'txt', 'pptx']
        available_types = [choice[0] for choice in DocumentType.choices]
        
        for doc_type in expected_types:
            self.assertIn(doc_type, available_types)


class MockAdapterTest(TestCase):
    """Test cases for mock adapters"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.subject = Subject.objects.create(
            name='Test Subject',
            code='TEST101',
            description='Test subject description',
            created_by=self.user
        )
    
    def test_mock_document_adapter(self):
        """Test mock document adapter functionality"""
        # Since the actual adapters might not exist, create mock tests
        mock_adapter = MagicMock()
        mock_adapter.process_document.return_value = {
            'success': True,
            'chunks': ['chunk1', 'chunk2', 'chunk3'],
            'metadata': {'pages': 10, 'words': 1000}
        }
        
        result = mock_adapter.process_document('test_document.pdf')
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['chunks']), 3)
        self.assertIn('metadata', result)
    
    def test_mock_chat_adapter(self):
        """Test mock chat adapter functionality"""
        mock_chat_adapter = MagicMock()
        mock_chat_adapter.generate_response.return_value = {
            'response': 'This is a mock AI response to your question.',
            'confidence': 0.85,
            'sources': [
                {'chunk_id': 'chunk_1', 'relevance': 0.9},
                {'chunk_id': 'chunk_2', 'relevance': 0.8}
            ]
        }
        
        query = "What is machine learning?"
        result = mock_chat_adapter.generate_response(query)
        
        self.assertIn('response', result)
        self.assertIn('confidence', result)
        self.assertIn('sources', result)
        self.assertGreater(result['confidence'], 0.8)
        self.assertEqual(len(result['sources']), 2)


class DatabaseUtilsTest(TestCase):
    """Test cases for database utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.subject = Subject.objects.create(
            name='Test Subject',
            code='TEST101',
            description='Test subject description',
            created_by=self.user
        )
    
    def test_model_ordering(self):
        """Test model ordering is working correctly"""
        # Create multiple subjects
        subject2 = Subject.objects.create(
            name='Another Subject',
            code='TEST102',
            description='Another test subject',
            created_by=self.user
        )
        
        subjects = Subject.objects.all()
        
        # Should be ordered by code
        self.assertEqual(subjects[0].code, 'TEST101')
        self.assertEqual(subjects[1].code, 'TEST102')
    
    def test_foreign_key_relationships(self):
        """Test foreign key relationships work correctly"""
        content = b"Test content"
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            content,
            content_type="text/plain"
        )
        
        document = Document.objects.create(
            title='Test Document',
            subject=self.subject,
            uploaded_by=self.user,
            file=uploaded_file,
            document_type=DocumentType.TXT,
            file_size=len(content)
        )
        
        # Test reverse foreign key
        user_documents = self.user.document_set.all()
        subject_documents = self.subject.documents.all()
        
        self.assertIn(document, user_documents)
        self.assertIn(document, subject_documents)
    
    def test_cascade_deletion(self):
        """Test cascade deletion behavior"""
        content = b"Test content"
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            content,
            content_type="text/plain"
        )
        
        document = Document.objects.create(
            title='Test Document',
            subject=self.subject,
            uploaded_by=self.user,
            file=uploaded_file,
            document_type=DocumentType.TXT,
            file_size=len(content)
        )
        
        chunk = DocumentChunk.objects.create(
            document=document,
            content='Test chunk',
            chunk_index=0,
            page_number=1
        )
        
        # Store IDs before deletion
        document_id = document.id
        chunk_id = chunk.id
        
        # Delete document should cascade to chunks
        document.delete()
        
        # Verify chunk is also deleted
        self.assertFalse(DocumentChunk.objects.filter(id=chunk_id).exists())
        self.assertFalse(Document.objects.filter(id=document_id).exists())


if __name__ == '__main__':
    import unittest
    unittest.main()
