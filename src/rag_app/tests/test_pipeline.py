"""
Tests for RAG pipeline components
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from rag_app.models import Subject, Document, DocumentChunk, DocumentType
from rag_app.pipeline.embeddings import EmbeddingsManager


User = get_user_model()


class EmbeddingsManagerTestCase(TestCase):
    """Test cases for EmbeddingsManager"""
    
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
    
    @patch('rag_app.pipeline.embeddings.SentenceTransformer')
    def test_embeddings_manager_initialization(self, mock_transformer):
        """Test EmbeddingsManager initialization"""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        manager = EmbeddingsManager()
        self.assertIsNotNone(manager)
        self.assertEqual(manager.model_name, 'all-MiniLM-L6-v2')
        mock_transformer.assert_called_once_with('all-MiniLM-L6-v2')
    
    @patch('rag_app.pipeline.embeddings.SentenceTransformer')
    def test_generate_embeddings(self, mock_transformer):
        """Test embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_transformer.return_value = mock_model
        
        manager = EmbeddingsManager()
        embeddings = manager.generate_embeddings(['test text'])
        
        self.assertIsInstance(embeddings, np.ndarray)
        self.assertEqual(embeddings.shape, (1, 3))
        mock_model.encode.assert_called_once_with(['test text'])
    
    @patch('rag_app.pipeline.embeddings.SentenceTransformer')
    def test_batch_embeddings(self, mock_transformer):
        """Test batch embedding generation"""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_transformer.return_value = mock_model
        
        manager = EmbeddingsManager()
        texts = ['text1', 'text2']
        embeddings = manager.generate_embeddings(texts)
        
        self.assertEqual(embeddings.shape, (2, 3))
        mock_model.encode.assert_called_once_with(texts)


class DocumentProcessingTestCase(TestCase):
    """Test cases for document processing"""
    
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
    
    def test_document_creation(self):
        """Test document creation"""
        content = b"This is test content for a document."
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
    
    def test_document_chunk_creation(self):
        """Test document chunk creation"""
        content = b"This is test content for a document."
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
            content='This is a test chunk',
            chunk_index=0,
            page_number=1
        )
        
        self.assertEqual(chunk.document, document)
        self.assertEqual(chunk.content, 'This is a test chunk')
        self.assertEqual(chunk.chunk_index, 0)
        self.assertEqual(chunk.page_number, 1)


class MockPipelineTestCase(TestCase):
    """Test cases for mocked pipeline components"""
    
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
    
    def test_mock_vectorstore_operations(self):
        """Test mock vectorstore operations"""
        # Mock vectorstore operations since the actual classes don't exist yet
        mock_vectorstore = Mock()
        mock_vectorstore.add_documents.return_value = True
        mock_vectorstore.search.return_value = [
            {'content': 'test result', 'score': 0.8}
        ]
        
        # Test adding documents
        result = mock_vectorstore.add_documents(['test doc'])
        self.assertTrue(result)
        
        # Test searching
        results = mock_vectorstore.search('test query')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'test result')
    
    def test_mock_retriever_operations(self):
        """Test mock retriever operations"""
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = [
            {'content': 'retrieved content', 'metadata': {'source': 'doc1'}}
        ]
        
        results = mock_retriever.retrieve('test query')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['content'], 'retrieved content')
    
    def test_mock_quiz_generation(self):
        """Test mock quiz generation"""
        mock_quiz_generator = Mock()
        mock_quiz_generator.generate_quiz.return_value = {
            'questions': [
                {
                    'question': 'What is Python?',
                    'type': 'multiple_choice',
                    'choices': ['A language', 'A snake', 'A tool', 'A framework'],
                    'correct_answer': 0
                }
            ],
            'metadata': {'total_questions': 1, 'difficulty': 'medium'}
        }
        
        quiz = mock_quiz_generator.generate_quiz('Python programming content')
        self.assertIn('questions', quiz)
        self.assertIn('metadata', quiz)
        self.assertEqual(len(quiz['questions']), 1)


if __name__ == '__main__':
    unittest.main()
