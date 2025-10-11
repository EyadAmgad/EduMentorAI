from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, 
    UpdateView, DeleteView, FormView
)
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseForbidden, HttpResponseServerError
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from io import BytesIO
import json
import logging
from .prompt_loader import prompt_loader
import os
import re
import glob

from .models import (
    Subject, Document, DocumentChunk, ChatSession, ChatMessage,
    Quiz, Question, UserProfile,
    TempDocument, AnswerChoice, QuizType
)
from .forms import (
    SubjectForm, DocumentUploadForm, QuizCreateForm, UserProfileForm,
    ChatMessageForm, ChatModeSelectionForm
)
from .pipeline.data_processor import DocumentProcessor
from .pipeline.SlideProcessor import SlideProcessor
from .pipeline.model import get_rag_model
from .email_service import GoogleAppsScriptEmailService
from .utils.email_utils import email_verification_manager, password_reset_manager

logger = logging.getLogger(__name__)


# EMAIL VERIFICATION VIEWS
def email_verification_required(request):
    """Show email verification required page"""
    if request.user.is_authenticated and request.user.is_active:
        return redirect('rag_app:dashboard')
    
    return render(request, 'rag_app/email_verification_required.html', {
        'user_email': request.user.email if request.user.is_authenticated else None
    })


def verify_email(request, token):
    """Handle email verification"""
    try:
        user = email_verification_manager.verify_token(token)
        
        if user:
            user.is_active = True
            user.save()
            login(request, user)
            messages.success(request, f'🎉 Welcome to EduMentorAI, {user.get_full_name() or user.username}! Your email has been verified successfully.')
            return redirect('rag_app:dashboard')
        else:
            messages.error(request, '❌ This verification link is invalid or expired. Please request a new verification email.')
            return redirect('rag_app:email_verification_required')
            
    except Exception as e:
        logger.error(f'Error during email verification: {str(e)}')
        messages.error(request, '⚠️ An error occurred during verification. Please try again or contact support.')
        return redirect('rag_app:email_verification_required')


def resend_verification_email(request):
    """Resend verification email"""
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to resend verification email.')
        return redirect('account_login')
    
    if request.user.is_active:
        messages.info(request, 'Your email is already verified!')
        return redirect('rag_app:dashboard')
    
    try:
        result = email_verification_manager.send_verification_email(request.user, request)
        
        if result.get('success'):
            messages.success(request, '📧 Verification email sent! Please check your inbox and spam folder.')
        else:
            messages.error(request, f'Failed to send verification email: {result.get("error", "Unknown error")}')
            
    except Exception as e:
        logger.error(f'Error resending verification email: {str(e)}')
        messages.error(request, 'An error occurred while sending the email. Please try again later.')
    
    return redirect('rag_app:email_verification_required')


def request_password_reset(request):
    """Handle password reset requests"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'registration/password_reset_form.html')
        
        try:
            user = User.objects.get(email=email, is_active=True)
            result = password_reset_manager.send_password_reset_email(user, request)
            
            if result.get('success'):
                messages.success(request, '📧 Password reset email sent! Please check your inbox and spam folder. The link will expire in 1 hour.')
                return redirect('rag_app:password_reset_done')
            else:
                messages.error(request, 'Failed to send password reset email. Please try again later.')
                
        except User.DoesNotExist:
            # Don't reveal whether email exists for security
            messages.success(request, '📧 If an account with that email exists, a password reset link has been sent.')
            return redirect('rag_app:password_reset_done')
        
        except Exception as e:
            logger.error(f'Error in password reset request: {str(e)}')
            messages.error(request, 'An error occurred while processing your request. Please try again later.')
    
    return render(request, 'registration/password_reset_form.html')


def reset_password_confirm(request, token):
    """Handle password reset confirmation"""
    user = password_reset_manager.verify_reset_token(token)
    
    if not user:
        messages.error(request, '❌ This password reset link is invalid or expired. Please request a new password reset.')
        return redirect('rag_app:request_password_reset')
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        
        if form.is_valid():
            try:
                consumed_user = password_reset_manager.consume_reset_token(token)
                
                if consumed_user:
                    form.save()
                    messages.success(request, '🔒 Your password has been reset successfully! You can now log in with your new password.')
                    return redirect('account_login')
                else:
                    messages.error(request, '❌ This password reset link has already been used or expired.')
                    return redirect('rag_app:request_password_reset')
                    
            except Exception as e:
                logger.error(f'Error completing password reset: {str(e)}')
                messages.error(request, 'An error occurred while resetting your password. Please try again.')
        
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'registration/password_reset_confirm.html', {
        'form': form,
        'user': user,
        'token': token
    })


def password_reset_done(request):
    """Show confirmation that password reset email was sent"""
    return render(request, 'registration/password_reset_done.html')


def clean_ai_response(response):
    """
    Clean AI response by removing think tags and fixing common formatting issues
    """
    if not response:
        return response
    
    # Remove <think> and </think> tags and their content
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up any extra whitespace that might be left
    response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)  # Replace multiple newlines with double newlines
    response = response.strip()
    
    return response


class ThinkTagFilter:
    """
    A stateful filter to remove <think></think> tags from streaming content
    """
    def __init__(self):
        self.buffer = ""
        self.inside_think = False
        self.think_buffer = ""
    
    def filter_chunk(self, chunk):
        """
        Filter a chunk of text, returning the clean content.
        Returns empty string if the chunk is part of think tags.
        """
        if not chunk:
            return chunk
            
        self.buffer += chunk
        output = ""
        
        while self.buffer:
            if not self.inside_think:
                # Look for opening think tag
                think_start = self.buffer.lower().find('<think>')
                if think_start == -1:
                    # No think tag found, output everything
                    output += self.buffer
                    self.buffer = ""
                    break
                else:
                    # Output everything before the think tag
                    output += self.buffer[:think_start]
                    self.buffer = self.buffer[think_start:]
                    self.inside_think = True
                    self.think_buffer = ""
            
            if self.inside_think:
                # Look for closing think tag
                think_end = self.buffer.lower().find('</think>')
                if think_end == -1:
                    # No closing tag yet, store in think buffer and wait for more
                    self.think_buffer += self.buffer
                    self.buffer = ""
                    break
                else:
                    # Found closing tag, skip everything including the tag
                    tag_end = think_end + len('</think>')
                    self.buffer = self.buffer[tag_end:]
                    self.inside_think = False
                    self.think_buffer = ""
        
        return output


class HomeView(TemplateView):
    """Landing page view"""
    template_name = 'rag_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['recent_subjects'] = Subject.objects.filter(
                created_by=self.request.user
            ).order_by('-created_at')[:5]
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    """User dashboard view"""
    template_name = 'rag_app/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user statistics
        context.update({
            'total_subjects': Subject.objects.filter(created_by=user).count(),
            'total_documents': Document.objects.filter(uploaded_by=user).count(),
            'total_quizzes': Quiz.objects.filter(created_by=user, google_form_url__isnull=False).count(),
            'recent_documents': Document.objects.filter(uploaded_by=user).order_by('-uploaded_at')[:5],
            'recent_quizzes': Quiz.objects.filter(created_by=user, google_form_url__isnull=False).order_by('-created_at')[:5],
            'recent_chat_sessions': ChatSession.objects.filter(user=user).order_by('-last_activity')[:5],
        })
        
        # Remove quiz attempts statistics since we're not tracking those anymore
        context['average_quiz_score'] = 0  # Not applicable for Google Forms
        
        return context


# Subject Views
class SubjectListView(LoginRequiredMixin, ListView):
    """List all subjects for the user"""
    model = Subject
    template_name = 'rag_app/subject_list.html'
    context_object_name = 'subjects'
    paginate_by = 10
    
    def get_queryset(self):
        return Subject.objects.filter(created_by=self.request.user)


class SubjectDetailView(LoginRequiredMixin, DetailView):
    """Subject detail view"""
    model = Subject
    template_name = 'rag_app/subject_detail.html'
    context_object_name = 'subject'
    
    def get_queryset(self):
        return Subject.objects.filter(created_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_object()
        context.update({
            'documents': subject.documents.all(),
            'quizzes': subject.quizzes.filter(google_form_url__isnull=False),  # Only Google Forms quizzes
            'document_count': subject.documents.count(),
            'quiz_count': subject.quizzes.filter(google_form_url__isnull=False).count(),
        })
        return context


class SubjectCreateView(LoginRequiredMixin, CreateView):
    """Create new subject"""
    model = Subject
    form_class = SubjectForm
    template_name = 'rag_app/subject_form.html'
    success_url = reverse_lazy('rag_app:subject_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Subject created successfully!')
        return super().form_valid(form)


class SubjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update existing subject"""
    model = Subject
    form_class = SubjectForm
    template_name = 'rag_app/subject_form.html'
    
    def get_queryset(self):
        return Subject.objects.filter(created_by=self.request.user)
    
    def get_success_url(self):
        return reverse('rag_app:subject_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Subject updated successfully!')
        return super().form_valid(form)


class SubjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete subject"""
    model = Subject
    template_name = 'rag_app/subject_confirm_delete.html'
    success_url = reverse_lazy('rag_app:subject_list')
    
    def get_queryset(self):
        return Subject.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Subject deleted successfully!')
        return super().delete(request, *args, **kwargs)


# Document Views
class DocumentListView(LoginRequiredMixin, ListView):
    """List all documents for the user"""
    model = Document
    template_name = 'rag_app/document_list.html'
    context_object_name = 'documents'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Document.objects.filter(uploaded_by=self.request.user)
        
        # Filter by subject
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        
        # Filter by search (title or content)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        
        # Filter by file type
        file_type = self.request.GET.get('file_type')
        if file_type:
            queryset = queryset.filter(document_type=file_type)
        
        # Sort
        sort_by = self.request.GET.get('sort', '-uploaded_at')
        if sort_by == 'uploaded_at':
            queryset = queryset.order_by('uploaded_at')
        elif sort_by == 'title':
            queryset = queryset.order_by('title')
        elif sort_by == '-title':
            queryset = queryset.order_by('-title')
        else:
            queryset = queryset.order_by('-uploaded_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(created_by=self.request.user)
        context['selected_subject'] = self.request.GET.get('subject')
        context['selected_file_type'] = self.request.GET.get('file_type')
        context['selected_sort'] = self.request.GET.get('sort', '-uploaded_at')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Document detail view"""
    model = Document
    template_name = 'rag_app/document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.get_object()
        context['chunks'] = document.chunks.all()[:10]  # Show first 10 chunks
        context['total_chunks'] = document.chunks.count()
        return context


class DocumentUploadView(LoginRequiredMixin, CreateView):
    """Upload new document"""
    model = Document
    form_class = DocumentUploadForm
    template_name = 'rag_app/document_upload.html'
    success_url = reverse_lazy('rag_app:document_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_subjects'] = Subject.objects.filter(created_by=self.request.user)
        return context
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        
        # Process document in background (in production, use Celery)
        try:
            processor = DocumentProcessor()
            processing_mode = form.instance.processing_mode
            
            if processing_mode == 'ocr':
                messages.info(self.request, 
                    'Document uploaded! Advanced processing with OCR is starting. This may take a few minutes...')
            else:
                messages.info(self.request, 
                    'Document uploaded! Fast processing is starting...')
            
            processor.process_document(self.object)
            
            if processing_mode == 'ocr':
                messages.success(self.request, 
                    'Document processed successfully with OCR! Images have been analyzed for text content.')
            else:
                messages.success(self.request, 
                    'Document processed successfully with fast mode!')
                
        except Exception as e:
            logger.error(f"Error processing document {self.object.id}: {str(e)}")
            messages.warning(self.request, 
                'Document uploaded but processing failed. Please try again or contact support.')
        
        return response


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete document"""
    model = Document
    template_name = 'rag_app/document_confirm_delete.html'
    success_url = reverse_lazy('rag_app:document_list')
    
    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Document deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def process_document(request, pk):
    """Process document for RAG"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    
    try:
        processor = DocumentProcessor()
        processor.process_document(document)
        messages.success(request, 'Document processed successfully!')
    except Exception as e:
        logger.error(f"Error processing document {pk}: {str(e)}")
        messages.error(request, 'Error processing document. Please try again.')
    
    return redirect('rag_app:document_detail', pk=pk)


@login_required
def reprocess_document(request, pk):
    """Reprocess document with different processing mode"""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    
    if request.method == 'POST':
        new_processing_mode = request.POST.get('processing_mode')
        
        if new_processing_mode in ['fast', 'ocr']:
            # Update the processing mode
            old_mode = document.processing_mode
            document.processing_mode = new_processing_mode
            document.processed = False  # Mark as unprocessed to trigger reprocessing
            document.save()
            
            try:
                processor = DocumentProcessor()
                processor.process_document(document)
                
                mode_name = 'Advanced OCR' if new_processing_mode == 'ocr' else 'Fast'
                messages.success(request, f'Document reprocessed successfully with {mode_name} mode!')
                
            except Exception as e:
                # Revert the processing mode if processing fails
                document.processing_mode = old_mode
                document.save()
                logger.error(f"Error reprocessing document {pk}: {str(e)}")
                messages.error(request, 'Error reprocessing document. Please try again.')
        else:
            messages.error(request, 'Invalid processing mode selected.')
    
    return redirect('rag_app:document_detail', pk=pk)


# Rest of your existing views continue here...
# (I'll continue with the remaining views in the next part due to length)

class ChatModeView(LoginRequiredMixin, View):
    """Chat mode selection view - choose between document chat or subject chat"""
    template_name = 'rag_app/chat_mode_selection.html'
    
    def get(self, request):
        """Show chat mode selection form"""
        form = ChatModeSelectionForm(user=request.user)
        
        context = {
            'form': form,
            'user_documents': Document.objects.filter(uploaded_by=request.user, processed=True).count(),
            'user_subjects': Subject.objects.filter(created_by=request.user).filter(
                documents__processed=True
            ).distinct().count(),
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle chat mode selection and redirect to appropriate chat"""
        form = ChatModeSelectionForm(request.POST, user=request.user)
        
        if form.is_valid():
            chat_mode = form.cleaned_data['chat_mode']
            
            if chat_mode == 'document':
                document = form.cleaned_data['document']
                # Create a new chat session for this specific document
                session = ChatSession.objects.create(
                    user=request.user,
                    title=f"Chat: {document.title}",
                    chat_type='document',
                    document=document  # We'll need to add this field to the model
                )
                return redirect('rag_app:chat_session', session_id=session.id)
            
            elif chat_mode == 'subject':
                subject = form.cleaned_data['subject']
                # Create a new chat session for this subject
                session = ChatSession.objects.create(
                    user=request.user,
                    subject=subject,
                    title=f"{subject.name} Chat",
                    chat_type='subject'
                )
                return redirect('rag_app:chat_session', session_id=session.id)
        
        context = {
            'form': form,
            'user_documents': Document.objects.filter(uploaded_by=request.user, processed=True).count(),
            'user_subjects': Subject.objects.filter(created_by=request.user).filter(
                documents__processed=True
            ).distinct().count(),
        }
        
        return render(request, self.template_name, context)


# Continue with remaining existing views...
class ProfileView(LoginRequiredMixin, View):
    """User profile view for viewing and updating profile"""
    
    def get(self, request):
        """Display user profile"""
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = UserProfile.objects.create(user=request.user)
        
        form = UserProfileForm(instance=profile, user=request.user)
        
        context = {
            'form': form,
            'profile': profile,
            'user': request.user
        }
        
        return render(request, 'rag_app/profile.html', context)
    
    def post(self, request):
        """Update user profile"""
        try:
            profile = request.user.userprofile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)
        
        form = UserProfileForm(
            request.POST, 
            request.FILES, 
            instance=profile, 
            user=request.user
        )
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('rag_app:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
        
        context = {
            'form': form,
            'profile': profile,
            'user': request.user
        }
        
        return render(request, 'rag_app/profile.html', context)
