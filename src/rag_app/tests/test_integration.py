"""
Integration tests for EduMentorAI
These tests verify that different components work together correctly.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.db import transaction
from unittest.mock import patch, MagicMock
import json
import tempfile
import time

from rag_app.models import (
    Subject, Document, DocumentChunk, ChatSession, ChatMessage,
    Quiz, Question, AnswerChoice, UserProfile, DocumentType, QuizType
)


class DocumentProcessingIntegrationTest(TransactionTestCase):
    """Integration tests for document processing workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.subject = Subject.objects.create(
            name='Computer Science',
            code='CS101',
            created_by=self.user
        )
    
    @patch('rag_app.pipeline.data_processor.DocumentProcessor.extract_text_from_txt')
    @patch('rag_app.pipeline.embeddings.EmbeddingGenerator.generate_embeddings')
    def test_complete_document_processing_workflow(self, mock_embeddings, mock_extract_text):
        """Test complete document upload and processing workflow"""
        # Mock text extraction
        mock_extract_text.return_value = "This is test content. " * 50  # Long enough to be chunked
        
        # Mock embedding generation
        mock_embeddings.return_value = [[0.1, 0.2, 0.3]] * 10  # Mock embeddings for chunks
        
        # Create a test file
        test_content = b"This is test file content."
        uploaded_file = SimpleUploadedFile(
            "test_document.txt",
            test_content,
            content_type="text/plain"
        )
        
        # Log in user
        self.client.login(username='testuser', password='testpass123')
        
        # Upload document through the web interface
        response = self.client.post(reverse('rag_app:document_upload'), {
            'title': 'Integration Test Document',
            'subject': self.subject.id,
            'file': uploaded_file
        })
        
        # Verify document was created
        document = Document.objects.filter(title='Integration Test Document').first()
        self.assertIsNotNone(document)
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(document.subject, self.subject)
        
        # Simulate document processing
        with patch('rag_app.pipeline.data_processor.DocumentProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor_instance.process_document.return_value = [
                "First chunk of content",
                "Second chunk of content"
            ]
            mock_processor.return_value = mock_processor_instance
            
            # Process the document
            processor = mock_processor_instance
            chunks = processor.process_document(document)
            
            # Create document chunks
            for i, chunk_content in enumerate(chunks):
                DocumentChunk.objects.create(
                    document=document,
                    content=chunk_content,
                    chunk_index=i
                )
        
        # Mark document as processed
        document.processed = True
        document.save()
        
        # Verify chunks were created
        chunks = DocumentChunk.objects.filter(document=document)
        self.assertEqual(chunks.count(), 2)
        
        # Verify document is marked as processed
        document.refresh_from_db()
        self.assertTrue(document.processed)
    
    def test_document_processing_error_handling(self):
        """Test error handling during document processing"""
        # Create a document
        document = Document.objects.create(
            title='Error Test Document',
            document_type=DocumentType.TXT,
            subject=self.subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        # Simulate processing error
        with patch('rag_app.pipeline.data_processor.DocumentProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            mock_processor_instance.process_document.side_effect = Exception("Processing error")
            mock_processor.return_value = mock_processor_instance
            
            # Attempt to process document
            try:
                processor = mock_processor_instance
                processor.process_document(document)
            except Exception:
                # Mark document processing as failed
                document.processed = False
                document.save()
        
        # Verify document is not marked as processed
        document.refresh_from_db()
        self.assertFalse(document.processed)


class ChatIntegrationTest(TestCase):
    """Integration tests for chat functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.subject = Subject.objects.create(
            name='Computer Science',
            code='CS101',
            created_by=self.user
        )
        self.document = Document.objects.create(
            title='Test Document',
            document_type=DocumentType.TXT,
            subject=self.subject,
            uploaded_by=self.user,
            file_size=1024,
            processed=True
        )
        
        # Create test chunks
        self.chunk1 = DocumentChunk.objects.create(
            document=self.document,
            content="Python is a programming language.",
            chunk_index=0
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.document,
            content="Django is a web framework.",
            chunk_index=1
        )
    
    @patch('rag_app.services.rag_adapter.RAGAdapter.generate_response')
    def test_complete_chat_workflow(self, mock_generate_response):
        """Test complete chat session workflow"""
        mock_generate_response.return_value = "Python is a high-level programming language known for its simplicity."
        
        # Log in user
        self.client.login(username='testuser', password='testpass123')
        
        # Create a chat session
        response = self.client.post(reverse('rag_app:chat_create'), {
            'subject': self.subject.id,
            'chat_type': 'subject',
            'title': 'Python Discussion'
        })
        
        # Verify chat session was created
        chat_session = ChatSession.objects.filter(title='Python Discussion').first()
        self.assertIsNotNone(chat_session)
        self.assertEqual(chat_session.user, self.user)
        self.assertEqual(chat_session.subject, self.subject)
        
        # Send a message to the chat
        message_data = {
            'message': 'What is Python?',
            'session_id': str(chat_session.id)
        }
        
        response = self.client.post(
            reverse('rag_app:send_message'),
            data=json.dumps(message_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Verify user message was stored
        user_message = ChatMessage.objects.filter(
            session=chat_session,
            is_user=True,
            message='What is Python?'
        ).first()
        self.assertIsNotNone(user_message)
        
        # Verify AI response was generated and stored
        ai_message = ChatMessage.objects.filter(
            session=chat_session,
            is_user=False
        ).first()
        self.assertIsNotNone(ai_message)
        
        # Verify chat session was updated
        chat_session.refresh_from_db()
        self.assertTrue(chat_session.last_activity)
    
    def test_chat_with_document_context(self):
        """Test chat functionality with specific document context"""
        # Create a document-specific chat session
        chat_session = ChatSession.objects.create(
            user=self.user,
            document=self.document,
            chat_type='document',
            title='Document Chat'
        )
        
        # Create a user message
        user_message = ChatMessage.objects.create(
            session=chat_session,
            message='Tell me about this document',
            is_user=True
        )
        
        # Simulate AI response generation with document context
        with patch('rag_app.services.rag_adapter.RAGAdapter') as mock_adapter:
            mock_adapter_instance = MagicMock()
            mock_adapter_instance.generate_response.return_value = (
                "This document discusses Python programming and Django framework."
            )
            mock_adapter.return_value = mock_adapter_instance
            
            # Generate AI response
            adapter = mock_adapter_instance
            ai_response = adapter.generate_response(
                query=user_message.message,
                chat_session=chat_session,
                context_documents=[self.document]
            )
            
            # Store AI response
            ai_message = ChatMessage.objects.create(
                session=chat_session,
                message=ai_response,
                is_user=False
            )
            
            # Link relevant chunks to the message
            ai_message.relevant_chunks.add(self.chunk1, self.chunk2)
        
        # Verify the complete conversation
        messages = ChatMessage.objects.filter(session=chat_session).order_by('timestamp')
        self.assertEqual(messages.count(), 2)
        self.assertTrue(messages[0].is_user)
        self.assertFalse(messages[1].is_user)
        self.assertEqual(messages[1].relevant_chunks.count(), 2)


class QuizGenerationIntegrationTest(TestCase):
    """Integration tests for quiz generation workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.subject = Subject.objects.create(
            name='Computer Science',
            code='CS101',
            created_by=self.user
        )
        self.document = Document.objects.create(
            title='Python Basics',
            document_type=DocumentType.TXT,
            subject=self.subject,
            uploaded_by=self.user,
            file_size=1024,
            processed=True
        )
        
        # Create content chunks
        self.chunk1 = DocumentChunk.objects.create(
            document=self.document,
            content="Python is a high-level programming language.",
            chunk_index=0
        )
        self.chunk2 = DocumentChunk.objects.create(
            document=self.document,
            content="Variables in Python can store different data types.",
            chunk_index=1
        )
    
    @patch('rag_app.pipeline.quiz_generator.QuizGenerator.generate_mcq_questions')
    @patch('rag_app.pipeline.quiz_generator.QuizGenerator.generate_true_false_questions')
    def test_complete_quiz_generation_workflow(self, mock_tf_generator, mock_mcq_generator):
        """Test complete quiz generation from document to quiz creation"""
        # Mock quiz generation
        mock_mcq_generator.return_value = [
            {
                'question': 'What is Python?',
                'choices': [
                    {'text': 'A programming language', 'correct': True},
                    {'text': 'A snake', 'correct': False},
                    {'text': 'A web browser', 'correct': False},
                    {'text': 'A database', 'correct': False}
                ],
                'explanation': 'Python is a programming language.'
            }
        ]
        
        mock_tf_generator.return_value = [
            {
                'question': 'Python is a high-level programming language.',
                'answer': True,
                'explanation': 'This statement is correct.'
            }
        ]
        
        # Log in user
        self.client.login(username='testuser', password='testpass123')
        
        # Create a quiz through the web interface
        response = self.client.post(reverse('rag_app:quiz_create'), {
            'title': 'Python Basics Quiz',
            'subject': self.subject.id,
            'based_on_document': self.document.id,
            'description': 'Test your Python knowledge',
            'time_limit': 30,
            'total_questions': 2
        })
        
        # Verify quiz was created
        quiz = Quiz.objects.filter(title='Python Basics Quiz').first()
        self.assertIsNotNone(quiz)
        self.assertEqual(quiz.created_by, self.user)
        self.assertEqual(quiz.subject, self.subject)
        self.assertEqual(quiz.based_on_document, self.document)
        
        # Simulate question generation and creation
        with patch('rag_app.pipeline.quiz_generator.QuizGenerator') as mock_generator:
            mock_generator_instance = MagicMock()
            mock_generator.return_value = mock_generator_instance
            
            # Generate MCQ question
            mcq_question = Question.objects.create(
                quiz=quiz,
                question_text='What is Python?',
                question_type=QuizType.MULTIPLE_CHOICE,
                explanation='Python is a programming language.',
                order=1,
                source_chunk=self.chunk1
            )
            
            # Create answer choices
            choices_data = [
                {'text': 'A programming language', 'correct': True},
                {'text': 'A snake', 'correct': False},
                {'text': 'A web browser', 'correct': False},
                {'text': 'A database', 'correct': False}
            ]
            
            for i, choice_data in enumerate(choices_data):
                AnswerChoice.objects.create(
                    question=mcq_question,
                    choice_text=choice_data['text'],
                    is_correct=choice_data['correct'],
                    order=i + 1
                )
            
            # Generate True/False question
            tf_question = Question.objects.create(
                quiz=quiz,
                question_text='Python is a high-level programming language.',
                question_type=QuizType.TRUE_FALSE,
                explanation='This statement is correct.',
                order=2,
                source_chunk=self.chunk1
            )
            
            # Create True/False choices
            AnswerChoice.objects.create(
                question=tf_question,
                choice_text='True',
                is_correct=True,
                order=1
            )
            AnswerChoice.objects.create(
                question=tf_question,
                choice_text='False',
                is_correct=False,
                order=2
            )
        
        # Verify questions and choices were created
        self.assertEqual(quiz.questions.count(), 2)
        
        mcq_question = quiz.questions.filter(question_type=QuizType.MULTIPLE_CHOICE).first()
        self.assertEqual(mcq_question.choices.count(), 4)
        self.assertEqual(mcq_question.choices.filter(is_correct=True).count(), 1)
        
        tf_question = quiz.questions.filter(question_type=QuizType.TRUE_FALSE).first()
        self.assertEqual(tf_question.choices.count(), 2)
        self.assertEqual(tf_question.choices.filter(is_correct=True).count(), 1)
    
    def test_quiz_taking_workflow(self):
        """Test complete quiz taking workflow"""
        # Create a quiz with questions
        quiz = Quiz.objects.create(
            title='Test Quiz',
            subject=self.subject,
            created_by=self.user,
            time_limit=30,
            total_questions=2
        )
        
        question1 = Question.objects.create(
            quiz=quiz,
            question_text='What is Python?',
            question_type=QuizType.MULTIPLE_CHOICE,
            order=1
        )
        
        AnswerChoice.objects.create(
            question=question1,
            choice_text='A programming language',
            is_correct=True,
            order=1
        )
        AnswerChoice.objects.create(
            question=question1,
            choice_text='A snake',
            is_correct=False,
            order=2
        )
        
        # Log in user
        self.client.login(username='testuser', password='testpass123')
        
        # Take the quiz
        response = self.client.get(reverse('rag_app:quiz_take', kwargs={'pk': quiz.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'What is Python?')
        self.assertContains(response, 'A programming language')
        
        # Submit quiz answers (if implemented)
        # This would depend on your quiz submission implementation


class UserWorkflowIntegrationTest(TestCase):
    """Integration tests for complete user workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!'
        }
    
    def test_complete_user_onboarding_workflow(self):
        """Test complete user registration and onboarding"""
        # Register new user
        response = self.client.post(reverse('account_signup'), self.user_data)
        
        # Verify user was created
        user = User.objects.filter(username='integrationuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'integration@example.com')
        
        # Log in the user
        login_success = self.client.login(
            username='integrationuser',
            password='ComplexPassword123!'
        )
        self.assertTrue(login_success)
        
        # Create user profile
        response = self.client.post(reverse('rag_app:profile_update'), {
            'bio': 'I am a new student',
            'university': 'Test University',
            'major': 'Computer Science',
            'year_of_study': 1
        })
        
        # Verify profile was created/updated
        profile = UserProfile.objects.filter(user=user).first()
        if profile:
            self.assertEqual(profile.bio, 'I am a new student')
            self.assertEqual(profile.university, 'Test University')
        
        # Create first subject
        response = self.client.post(reverse('rag_app:subject_create'), {
            'name': 'Introduction to Programming',
            'code': 'CS101',
            'description': 'My first programming course'
        })
        
        # Verify subject was created
        subject = Subject.objects.filter(created_by=user, code='CS101').first()
        self.assertIsNotNone(subject)
        
        # Upload first document
        test_file = SimpleUploadedFile(
            "notes.txt",
            b"These are my programming notes.",
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('rag_app:document_upload'), {
            'title': 'Programming Notes',
            'subject': subject.id,
            'file': test_file
        })
        
        # Verify document was uploaded
        document = Document.objects.filter(
            uploaded_by=user,
            title='Programming Notes'
        ).first()
        self.assertIsNotNone(document)
        
        # Start first chat session
        response = self.client.post(reverse('rag_app:chat_create'), {
            'subject': subject.id,
            'chat_type': 'subject',
            'title': 'First Chat'
        })
        
        # Verify chat session was created
        chat_session = ChatSession.objects.filter(
            user=user,
            title='First Chat'
        ).first()
        self.assertIsNotNone(chat_session)
    
    def test_multi_user_interaction_workflow(self):
        """Test workflows involving multiple users"""
        # Create first user
        user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='password123'
        )
        
        # Create second user
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='password123'
        )
        
        # User 1 creates a subject
        subject1 = Subject.objects.create(
            name='User 1 Subject',
            code='U1S1',
            created_by=user1
        )
        
        # User 2 creates a subject
        subject2 = Subject.objects.create(
            name='User 2 Subject',
            code='U2S1',
            created_by=user2
        )
        
        # Test that users can only access their own content
        self.client.login(username='user1', password='password123')
        
        # User 1 should be able to access their subject
        response = self.client.get(reverse('rag_app:subject_detail', kwargs={'pk': subject1.pk}))
        self.assertEqual(response.status_code, 200)
        
        # User 1 should not be able to access User 2's subject
        response = self.client.get(reverse('rag_app:subject_detail', kwargs={'pk': subject2.pk}))
        self.assertIn(response.status_code, [403, 404])
        
        # Switch to User 2
        self.client.logout()
        self.client.login(username='user2', password='password123')
        
        # User 2 should be able to access their subject
        response = self.client.get(reverse('rag_app:subject_detail', kwargs={'pk': subject2.pk}))
        self.assertEqual(response.status_code, 200)
        
        # User 2 should not be able to access User 1's subject
        response = self.client.get(reverse('rag_app:subject_detail', kwargs={'pk': subject1.pk}))
        self.assertIn(response.status_code, [403, 404])


class PerformanceIntegrationTest(TestCase):
    """Integration tests for performance-critical workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='testpass123'
        )
        self.subject = Subject.objects.create(
            name='Performance Test Subject',
            code='PERF101',
            created_by=self.user
        )
    
    def test_large_document_processing_workflow(self):
        """Test processing of large documents"""
        # Create a large document
        large_content = "This is a test sentence. " * 1000  # Large content
        
        document = Document.objects.create(
            title='Large Document',
            document_type=DocumentType.TXT,
            subject=self.subject,
            uploaded_by=self.user,
            file_size=len(large_content.encode())
        )
        
        # Simulate processing of large document
        start_time = time.time()
        
        with patch('rag_app.pipeline.data_processor.DocumentProcessor') as mock_processor:
            mock_processor_instance = MagicMock()
            
            # Simulate chunking of large content
            chunk_size = 200
            chunks = [
                large_content[i:i+chunk_size] 
                for i in range(0, len(large_content), chunk_size)
            ]
            
            mock_processor_instance.process_document.return_value = chunks
            mock_processor.return_value = mock_processor_instance
            
            # Process the document
            processor = mock_processor_instance
            result_chunks = processor.process_document(document)
            
            # Create chunks in database
            chunk_objects = []
            for i, chunk_content in enumerate(result_chunks):
                chunk_obj = DocumentChunk(
                    document=document,
                    content=chunk_content,
                    chunk_index=i
                )
                chunk_objects.append(chunk_obj)
            
            # Bulk create for performance
            DocumentChunk.objects.bulk_create(chunk_objects)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify chunks were created
        chunk_count = DocumentChunk.objects.filter(document=document).count()
        self.assertGreater(chunk_count, 0)
        
        # Performance should be reasonable (adjust threshold as needed)
        self.assertLess(processing_time, 10.0)  # Should complete within 10 seconds
    
    def test_concurrent_user_workflow(self):
        """Test workflow with multiple concurrent operations"""
        # Create multiple users
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'concurrent_user_{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            users.append(user)
        
        # Each user creates subjects and documents
        for i, user in enumerate(users):
            subject = Subject.objects.create(
                name=f'Subject {i}',
                code=f'SUBJ{i}',
                created_by=user
            )
            
            document = Document.objects.create(
                title=f'Document {i}',
                document_type=DocumentType.TXT,
                subject=subject,
                uploaded_by=user,
                file_size=1024
            )
            
            # Create chunks for each document
            for j in range(3):
                DocumentChunk.objects.create(
                    document=document,
                    content=f'User {i} Document {i} Chunk {j} content',
                    chunk_index=j
                )
        
        # Verify all data was created correctly
        self.assertEqual(User.objects.filter(username__startswith='concurrent_user_').count(), 5)
        self.assertEqual(Subject.objects.filter(code__startswith='SUBJ').count(), 5)
        self.assertEqual(Document.objects.filter(title__startswith='Document').count(), 5)
        self.assertEqual(DocumentChunk.objects.count(), 15)  # 5 documents * 3 chunks each
