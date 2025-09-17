from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Subject, Document, DocumentChunk, ChatSession, ChatMessage,
    Quiz, Question, AnswerChoice, QuizAttempt, QuizResponse,
    UserProfile, StudySession
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_by', 'created_at', 'document_count']
    list_filter = ['created_at', 'created_by']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at']
    
    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Documents'


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ['chunk_index', 'page_number', 'created_at']
    fields = ['chunk_index', 'page_number', 'content', 'created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'subject', 'uploaded_by', 
                   'uploaded_at', 'processed', 'file_size_display', 'chunk_count']
    list_filter = ['document_type', 'processed', 'uploaded_at', 'subject']
    search_fields = ['title', 'uploaded_by__username', 'subject__name']
    readonly_fields = ['id', 'uploaded_at', 'processed_at', 'file_size', 'page_count']
    inlines = [DocumentChunkInline]
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size > 1024 * 1024:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
            elif obj.file_size > 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size} bytes"
        return "Unknown"
    file_size_display.short_description = 'File Size'
    
    def chunk_count(self, obj):
        return obj.chunks.count()
    chunk_count.short_description = 'Chunks'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'page_number', 'content_preview', 'created_at']
    list_filter = ['created_at', 'document__document_type']
    search_fields = ['content', 'document__title']
    readonly_fields = ['id', 'created_at', 'embedding_vector']
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['timestamp', 'response_time']
    fields = ['message', 'is_user', 'timestamp', 'response_time']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'subject', 'created_at', 'last_activity', 'message_count']
    list_filter = ['created_at', 'last_activity', 'subject']
    search_fields = ['title', 'user__username', 'subject__name']
    readonly_fields = ['id', 'created_at', 'last_activity']
    inlines = [ChatMessageInline]
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'message_preview', 'is_user', 'timestamp', 'response_time']
    list_filter = ['is_user', 'timestamp']
    search_fields = ['message', 'session__title', 'session__user__username']
    readonly_fields = ['id', 'timestamp']
    
    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 4
    fields = ['order', 'choice_text', 'is_correct']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['order', 'question_text', 'question_type', 'points']
    readonly_fields = ['id']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'created_by', 'created_at', 
                   'total_questions', 'time_limit', 'is_active', 'attempt_count']
    list_filter = ['created_at', 'is_active', 'subject', 'time_limit']
    search_fields = ['title', 'description', 'created_by__username', 'subject__name']
    readonly_fields = ['id', 'created_at']
    inlines = [QuestionInline]
    
    def attempt_count(self, obj):
        return obj.attempts.count()
    attempt_count.short_description = 'Attempts'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'order', 'question_preview', 'question_type', 'points']
    list_filter = ['question_type', 'quiz__subject']
    search_fields = ['question_text', 'quiz__title']
    readonly_fields = ['id']
    inlines = [AnswerChoiceInline]
    
    def question_preview(self, obj):
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_preview.short_description = 'Question'


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', 'order', 'choice_preview', 'is_correct']
    list_filter = ['is_correct', 'question__question_type']
    search_fields = ['choice_text', 'question__question_text']
    
    def choice_preview(self, obj):
        return obj.choice_text[:30] + "..." if len(obj.choice_text) > 30 else obj.choice_text
    choice_preview.short_description = 'Choice'


class QuizResponseInline(admin.TabularInline):
    model = QuizResponse
    extra = 0
    readonly_fields = ['answered_at', 'is_correct', 'points_earned']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'user', 'started_at', 'completed_at', 
                   'is_completed', 'score', 'time_taken']
    list_filter = ['is_completed', 'started_at', 'quiz__subject']
    search_fields = ['user__username', 'quiz__title']
    readonly_fields = ['id', 'started_at', 'time_taken']
    inlines = [QuizResponseInline]


@admin.register(QuizResponse)
class QuizResponseAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'selected_choice', 'is_correct', 
                   'points_earned', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
    search_fields = ['attempt__user__username', 'question__question_text']
    readonly_fields = ['answered_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'university', 'major', 'year_of_study', 'created_at']
    list_filter = ['university', 'major', 'year_of_study', 'created_at']
    search_fields = ['user__username', 'user__email', 'university', 'major']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly_fields.append('user')
        return readonly_fields


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'started_at', 'ended_at', 
                   'duration', 'questions_asked', 'quizzes_taken']
    list_filter = ['started_at', 'subject']
    search_fields = ['user__username', 'subject__name']
    readonly_fields = ['id', 'started_at', 'duration']
    filter_horizontal = ['documents_accessed']


# Customize admin site
admin.site.site_header = "EduMentorAI Administration"
admin.site.site_title = "EduMentorAI Admin"
admin.site.index_title = "Welcome to EduMentorAI Administration"
