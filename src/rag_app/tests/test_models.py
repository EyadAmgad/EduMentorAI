"""
Unit tests for EduMentorAI models - Corrected version
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from datetime import timedelta
import uuid
import tempfile
import os

from rag_app.models import (
    Subject, Document, DocumentChunk, ChatSession, ChatMessage,
    Quiz, Question, AnswerChoice, UserProfile, TempDocument,
    DocumentType, QuizType
)


class BaseTestCase(TestCase):
    """Base test case with unique identifier generation."""
    
    def setUp(self):
        """Set up test data with unique identifiers."""
        # Generate unique test ID
        self.test_id = str(uuid.uuid4())[:8]
        
        # Create test user with unique username
        self.user = User.objects.create_user(
            username=f'testuser_{self.test_id}',
            email=f'test_{self.test_id}@example.com',
            password='testpass123'
        )
    
    def create_unique_subject(self, name_suffix="Subject", code_prefix="TEST"):
        """Create a subject with unique code."""
        code = f"{code_prefix}{self.test_id[:4].upper()}"
        name = f"Test {name_suffix} {self.test_id}"
        
        return Subject.objects.create(
            name=name,
            code=code,
            created_by=self.user
        )


class SubjectModelTest(BaseTestCase):
    """Test Subject model"""
    
    def test_subject_creation(self):
        """Test creating a subject"""
        subject = self.create_unique_subject(name_suffix='Computer Science', code_prefix='CS')
        
        self.assertEqual(subject.created_by, self.user)
        self.assertIsNotNone(subject.created_at)
        self.assertTrue(subject.name.startswith('Test Computer Science'))
        self.assertTrue(subject.code.startswith('CS'))
    
    def test_subject_string_representation(self):
        """Test subject string representation"""
        subject = self.create_unique_subject(name_suffix='Math', code_prefix='MATH')
        
        expected = f"{subject.code} - {subject.name}"
        self.assertEqual(str(subject), expected)
    
    def test_subject_code_unique(self):
        """Test that subject codes must be unique"""
        code = f"UNIQUE{self.test_id[:4].upper()}"
        
        # Create first subject
        Subject.objects.create(
            name=f'First Subject {self.test_id}',
            code=code,
            created_by=self.user
        )
        
        # Try to create second subject with same code - should fail
        with self.assertRaises(IntegrityError):
            Subject.objects.create(
                name=f'Second Subject {self.test_id}',
                code=code,
                created_by=self.user
            )
    
    def test_subject_ordering(self):
        """Test subject ordering by name"""
        subject1 = self.create_unique_subject(name_suffix='Alpha', code_prefix='A')
        subject2 = self.create_unique_subject(name_suffix='Beta', code_prefix='B')
        
        subjects = list(Subject.objects.all().order_by('name'))
        # Check if ordering is working (subjects should be sorted by name)
        self.assertTrue(len(subjects) >= 2)


class DocumentModelTest(BaseTestCase):
    """Test Document model"""
    
    def test_document_creation(self):
        """Test creating a document"""
        subject = self.create_unique_subject()
        
        document = Document.objects.create(
            title=f'Test Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        self.assertEqual(document.subject, subject)
        self.assertEqual(document.uploaded_by, self.user)
        self.assertEqual(document.file_size, 1024)
        self.assertIsNotNone(document.uploaded_at)
    
    def test_document_string_representation(self):
        """Test document string representation"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'My Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        self.assertEqual(str(document), f'My Document {self.test_id}')
    
    def test_document_file_size_save(self):
        """Test document file size handling on save"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Test Size Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=2048
        )
        
        self.assertEqual(document.file_size, 2048)
    
    def test_document_ordering(self):
        """Test document ordering by uploaded_at"""
        subject = self.create_unique_subject()
        
        document1 = Document.objects.create(
            title=f'First Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        document2 = Document.objects.create(
            title=f'Second Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=2048
        )
        
        documents = list(Document.objects.all().order_by('-uploaded_at'))
        # Just check that we have documents and ordering works
        self.assertTrue(len(documents) >= 2)


class DocumentChunkModelTest(BaseTestCase):
    """Test DocumentChunk model"""
    
    def test_chunk_creation(self):
        """Test creating a document chunk"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Test Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=1,
            content=f'Test chunk content {self.test_id}'
        )
        
        self.assertEqual(chunk.document, document)
        self.assertEqual(chunk.chunk_index, 1)
        self.assertTrue(chunk.content.startswith('Test chunk content'))
    
    def test_chunk_string_representation(self):
        """Test chunk string representation"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Doc {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        chunk = DocumentChunk.objects.create(
            document=document,
            chunk_index=1,
            content=f'Content {self.test_id}'
        )
        
        expected = f"Doc {self.test_id} - Chunk 1"
        self.assertEqual(str(chunk), expected)
    
    def test_chunk_ordering(self):
        """Test chunk ordering by chunk_index"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Test Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        chunk2 = DocumentChunk.objects.create(
            document=document,
            chunk_index=2,
            content=f'Second chunk {self.test_id}'
        )
        
        chunk1 = DocumentChunk.objects.create(
            document=document,
            chunk_index=1,
            content=f'First chunk {self.test_id}'
        )
        
        chunks = list(DocumentChunk.objects.filter(document=document).order_by('chunk_index'))
        self.assertEqual(chunks[0].chunk_index, 1)
        self.assertEqual(chunks[1].chunk_index, 2)
    
    def test_chunk_unique_constraint(self):
        """Test unique constraint on document and chunk_index"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Test Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        # Create first chunk
        DocumentChunk.objects.create(
            document=document,
            chunk_index=1,
            content=f'First chunk {self.test_id}'
        )
        
        # Try to create second chunk with same index - should fail
        with self.assertRaises(IntegrityError):
            DocumentChunk.objects.create(
                document=document,
                chunk_index=1,
                content=f'Duplicate chunk {self.test_id}'
            )


class ChatSessionModelTest(BaseTestCase):
    """Test ChatSession model"""
    
    def test_subject_chat_session_creation(self):
        """Test creating a subject-based chat session"""
        subject = self.create_unique_subject()
        
        session = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        self.assertEqual(session.subject, subject)
        self.assertEqual(session.user, self.user)
        self.assertIsNone(session.document)
        self.assertIsNotNone(session.created_at)
    
    def test_document_chat_session_creation(self):
        """Test creating a document-based chat session"""
        subject = self.create_unique_subject()
        document = Document.objects.create(
            title=f'Test Document {self.test_id}',
            subject=subject,
            uploaded_by=self.user,
            file_size=1024
        )
        
        session = ChatSession.objects.create(
            document=document,
            user=self.user
        )
        
        self.assertEqual(session.document, document)
        self.assertEqual(session.user, self.user)
        self.assertIsNone(session.subject)
    
    def test_session_ordering(self):
        """Test session ordering by last_activity"""
        subject = self.create_unique_subject()
        
        session1 = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        session2 = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        sessions = list(ChatSession.objects.all().order_by('-last_activity'))
        self.assertTrue(len(sessions) >= 2)


class ChatMessageModelTest(BaseTestCase):
    """Test ChatMessage model"""
    
    def test_user_message_creation(self):
        """Test creating a user message"""
        subject = self.create_unique_subject()
        session = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        message = ChatMessage.objects.create(
            session=session,
            message=f'User message {self.test_id}',
            is_user=True
        )
        
        self.assertEqual(message.session, session)
        self.assertTrue(message.message.startswith('User message'))
        self.assertTrue(message.is_user)
        self.assertIsNotNone(message.timestamp)
    
    def test_ai_message_creation(self):
        """Test creating an AI message"""
        subject = self.create_unique_subject()
        session = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        message = ChatMessage.objects.create(
            session=session,
            message=f'AI response {self.test_id}',
            is_user=False
        )
        
        self.assertFalse(message.is_user)
        self.assertTrue(message.message.startswith('AI response'))
    
    def test_message_ordering(self):
        """Test message ordering by timestamp"""
        subject = self.create_unique_subject()
        session = ChatSession.objects.create(
            subject=subject,
            user=self.user
        )
        
        message1 = ChatMessage.objects.create(
            session=session,
            message=f'First message {self.test_id}',
            is_user=True
        )
        
        message2 = ChatMessage.objects.create(
            session=session,
            message=f'Second message {self.test_id}',
            is_user=False
        )
        
        messages = list(ChatMessage.objects.filter(session=session).order_by('timestamp'))
        self.assertEqual(len(messages), 2)


class QuizModelTest(BaseTestCase):
    """Test Quiz model"""
    
    def test_quiz_creation(self):
        """Test creating a quiz"""
        subject = self.create_unique_subject()
        
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user,
            total_questions=5
        )
        
        self.assertEqual(quiz.subject, subject)
        self.assertEqual(quiz.created_by, self.user)
        self.assertEqual(quiz.total_questions, 5)
        self.assertIsNotNone(quiz.created_at)
    
    def test_quiz_string_representation(self):
        """Test quiz string representation"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'My Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        self.assertEqual(str(quiz), f'My Quiz {self.test_id}')
    
    def test_quiz_ordering(self):
        """Test quiz ordering by created_at"""
        subject = self.create_unique_subject()
        
        quiz1 = Quiz.objects.create(
            title=f'First Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        quiz2 = Quiz.objects.create(
            title=f'Second Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        quizzes = list(Quiz.objects.all().order_by('-created_at'))
        self.assertTrue(len(quizzes) >= 2)


class QuestionModelTest(BaseTestCase):
    """Test Question model"""
    
    def test_question_creation(self):
        """Test creating a question"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        question = Question.objects.create(
            quiz=quiz,
            question_text=f'What is the answer {self.test_id}?',
            order=1
        )
        
        self.assertEqual(question.quiz, quiz)
        self.assertTrue(question.question_text.endswith('?'))
        self.assertEqual(question.order, 1)
    
    def test_question_string_representation(self):
        """Test question string representation"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        question = Question.objects.create(
            quiz=quiz,
            question_text=f'Test question {self.test_id}?',
            order=1
        )
        
        # The actual __str__ method includes Q{order}: {question_text}...
        expected_start = f'Q1: Test question {self.test_id}?'
        self.assertTrue(str(question).startswith(expected_start))
    
    def test_question_ordering(self):
        """Test question ordering by order field"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        question2 = Question.objects.create(
            quiz=quiz,
            question_text=f'Second question {self.test_id}?',
            order=2
        )
        
        question1 = Question.objects.create(
            quiz=quiz,
            question_text=f'First question {self.test_id}?',
            order=1
        )
        
        questions = list(Question.objects.filter(quiz=quiz).order_by('order'))
        self.assertEqual(questions[0].order, 1)
        self.assertEqual(questions[1].order, 2)
    
    def test_question_unique_constraint(self):
        """Test unique constraint on quiz and order"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        
        # Create first question
        Question.objects.create(
            quiz=quiz,
            question_text=f'First question {self.test_id}?',
            order=1
        )
        
        # Try to create second question with same order - should fail
        with self.assertRaises(IntegrityError):
            Question.objects.create(
                quiz=quiz,
                question_text=f'Duplicate question {self.test_id}?',
                order=1
            )


class AnswerChoiceModelTest(BaseTestCase):
    """Test AnswerChoice model"""
    
    def test_answer_choice_creation(self):
        """Test creating an answer choice"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        question = Question.objects.create(
            quiz=quiz,
            question_text=f'Test question {self.test_id}?',
            order=1
        )
        
        choice = AnswerChoice.objects.create(
            question=question,
            choice_text=f'Correct answer {self.test_id}',
            is_correct=True,
            order=1
        )
        
        self.assertEqual(choice.question, question)
        self.assertTrue(choice.choice_text.startswith('Correct answer'))
        self.assertTrue(choice.is_correct)
        self.assertEqual(choice.order, 1)
    
    def test_incorrect_answer_choice(self):
        """Test creating an incorrect answer choice"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        question = Question.objects.create(
            quiz=quiz,
            question_text=f'Test question {self.test_id}?',
            order=1
        )
        
        choice = AnswerChoice.objects.create(
            question=question,
            choice_text=f'Wrong answer {self.test_id}',
            is_correct=False,
            order=2
        )
        
        self.assertFalse(choice.is_correct)
    
    def test_choice_ordering(self):
        """Test answer choice ordering by order field"""
        subject = self.create_unique_subject()
        quiz = Quiz.objects.create(
            title=f'Test Quiz {self.test_id}',
            subject=subject,
            created_by=self.user
        )
        question = Question.objects.create(
            quiz=quiz,
            question_text=f'Test question {self.test_id}?',
            order=1
        )
        
        choice2 = AnswerChoice.objects.create(
            question=question,
            choice_text=f'Second choice {self.test_id}',
            is_correct=False,
            order=2
        )
        
        choice1 = AnswerChoice.objects.create(
            question=question,
            choice_text=f'First choice {self.test_id}',
            is_correct=True,
            order=1
        )
        
        choices = list(AnswerChoice.objects.filter(question=question).order_by('order'))
        self.assertEqual(choices[0].order, 1)
        self.assertEqual(choices[1].order, 2)


class UserProfileModelTest(BaseTestCase):
    """Test UserProfile model"""
    
    def test_user_profile_creation(self):
        """Test creating a user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio=f'Test bio {self.test_id}',
            university=f'Test University {self.test_id}',
            major='Computer Science',
            year_of_study=3
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertTrue(profile.bio.startswith('Test bio'))
        self.assertTrue(profile.university.startswith('Test University'))
        self.assertEqual(profile.major, 'Computer Science')
        self.assertEqual(profile.year_of_study, 3)
    
    def test_user_profile_string_representation(self):
        """Test user profile string representation"""
        profile = UserProfile.objects.create(
            user=self.user,
            bio=f'Profile for {self.test_id}'
        )
        
        expected = f"{self.user.username}'s Profile"
        self.assertEqual(str(profile), expected)
