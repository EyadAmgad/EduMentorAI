from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import os


def upload_to_user_folder(instance, filename):
    """Upload files to user-specific folders"""
    return f'uploads/{instance.uploaded_by.id}/{filename}'


class DocumentType(models.TextChoices):
    """Document type choices"""
    PDF = 'pdf', 'PDF'
    DOCX = 'docx', 'Word Document'
    TXT = 'txt', 'Text File'
    PPTX = 'pptx', 'PowerPoint'


class Subject(models.Model):
    """Subject/Course model"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        ordering = ['code']


class Document(models.Model):
    """Uploaded document model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_to_user_folder)
    document_type = models.CharField(max_length=10, choices=DocumentType.choices)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    file_size = models.PositiveIntegerField()  # in bytes
    page_count = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            # Auto-detect document type from file extension
            ext = os.path.splitext(self.file.name)[1].lower().lstrip('.')
            if ext in ['pdf', 'docx', 'txt', 'pptx']:
                self.document_type = ext
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-uploaded_at']


class DocumentChunk(models.Model):
    """Processed document chunks for RAG"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    embedding_vector = models.BinaryField(null=True, blank=True)  # Store embeddings
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"
    
    class Meta:
        ordering = ['chunk_index']
        unique_together = ['document', 'chunk_index']


class ChatSession(models.Model):
    """Chat session model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chat - {self.user.username} - {self.title or 'Untitled'}"
    
    class Meta:
        ordering = ['-last_activity']


class ChatMessage(models.Model):
    """Individual chat messages"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    is_user = models.BooleanField()  # True for user messages, False for AI responses
    timestamp = models.DateTimeField(auto_now_add=True)
    response_time = models.FloatField(null=True, blank=True)  # AI response time in seconds
    relevant_chunks = models.ManyToManyField(DocumentChunk, blank=True)
    
    def __str__(self):
        sender = "User" if self.is_user else "AI"
        return f"{sender}: {self.message[:50]}..."
    
    class Meta:
        ordering = ['timestamp']


class QuizType(models.TextChoices):
    """Quiz type choices"""
    MULTIPLE_CHOICE = 'mcq', 'Multiple Choice'
    TRUE_FALSE = 'tf', 'True/False'
    SHORT_ANSWER = 'sa', 'Short Answer'
    FILL_BLANK = 'fb', 'Fill in the Blank'


class Quiz(models.Model):
    """Generated quiz model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    based_on_document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)
    time_limit = models.PositiveIntegerField(default=30)  # in minutes
    total_questions = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']


class Question(models.Model):
    """Quiz question model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QuizType.choices)
    points = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True)
    source_chunk = models.ForeignKey(DocumentChunk, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.PositiveIntegerField()
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}..."
    
    class Meta:
        ordering = ['order']
        unique_together = ['quiz', 'order']


class AnswerChoice(models.Model):
    """Multiple choice answer options"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField()
    
    def __str__(self):
        return f"{self.choice_text[:30]}... ({'✓' if self.is_correct else '✗'})"
    
    class Meta:
        ordering = ['order']
        unique_together = ['question', 'order']


class QuizAttempt(models.Model):
    """User quiz attempts"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)  # Percentage score
    total_points = models.PositiveIntegerField(default=0)
    earned_points = models.PositiveIntegerField(default=0)
    time_taken = models.DurationField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        status = "Completed" if self.is_completed else "In Progress"
        return f"{self.user.username} - {self.quiz.title} ({status})"
    
    def calculate_score(self):
        """Calculate and update the score"""
        if self.total_points > 0:
            self.score = (self.earned_points / self.total_points) * 100
        else:
            self.score = 0
        self.save()
    
    class Meta:
        ordering = ['-started_at']


class QuizResponse(models.Model):
    """Individual question responses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(AnswerChoice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True)  # For short answer questions
    is_correct = models.BooleanField(default=False)
    points_earned = models.PositiveIntegerField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.question.question_text[:30]}... - {self.attempt.user.username}"
    
    class Meta:
        unique_together = ['attempt', 'question']


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    university = models.CharField(max_length=200, blank=True)
    major = models.CharField(max_length=100, blank=True)
    year_of_study = models.PositiveIntegerField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class StudySession(models.Model):
    """Track user study sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    documents_accessed = models.ManyToManyField(Document, blank=True)
    questions_asked = models.PositiveIntegerField(default=0)
    quizzes_taken = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.subject.name} - {self.started_at.date()}"
    
    class Meta:
        ordering = ['-started_at']
