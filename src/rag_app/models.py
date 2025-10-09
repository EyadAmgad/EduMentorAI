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


class ProcessingMode(models.TextChoices):
    """Document processing mode choices"""
    FAST = 'fast', 'Fast Processing (Text Only)'
    OCR = 'ocr', 'Advanced Processing (Text + OCR for Images)'


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
    processing_mode = models.CharField(max_length=10, choices=ProcessingMode.choices, default=ProcessingMode.FAST)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    file_size = models.PositiveIntegerField()  # in bytes
    page_count = models.PositiveIntegerField(null=True, blank=True)
    
    # Processed text: Combined extracted text + OCR text from images
    processed_text = models.TextField(blank=True, help_text="Clean text-only version (document text + OCR text)")
    
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


class DocumentImage(models.Model):
    """Extracted images from documents with OCR text"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='images')
    image_file = models.ImageField(upload_to='document_images/')
    page_number = models.PositiveIntegerField()
    image_index = models.PositiveIntegerField()  # Index of image on the page
    ocr_text = models.TextField(blank=True)  # Extracted text from OCR
    ocr_processed = models.BooleanField(default=False)
    embedding_vector = models.BinaryField(null=True, blank=True)  # Store OCR text embeddings
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.document.title} - Page {self.page_number} - Image {self.image_index}"
    
    class Meta:
        ordering = ['page_number', 'image_index']
        unique_together = ['document', 'page_number', 'image_index']


class ChatSession(models.Model):
    """Chat session model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_chats")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name="subject_chats")
    # For specific document chat
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True, related_name="document_chats")
    # For anonymous document chat
    temp_document = models.ForeignKey('TempDocument', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=255, blank=True)
    chat_type = models.CharField(max_length=20, choices=[
        ('subject', 'Subject Chat'),
        ('document', 'Document Chat'),
        ('anonymous', 'Anonymous Chat')
    ], default='subject')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chat - {self.user.username} - {self.title or 'Untitled'}"
    
    class Meta:
        ordering = ['-last_activity']


class TempDocument(models.Model):
    """Temporary document for anonymous chat sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='temp_documents/')
    processing_mode = models.CharField(max_length=10, choices=ProcessingMode.choices, default=ProcessingMode.FAST)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField()  # in bytes
    # Auto-delete after 24 hours
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Temp: {self.title}"
    
    class Meta:
        ordering = ['-uploaded_at']


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
    # Optional Google Form integration
    google_form_url = models.URLField(null=True, blank=True)
    google_form_edit_url = models.URLField(null=True, blank=True)
    google_form_owner_email = models.EmailField(null=True, blank=True)
    
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
