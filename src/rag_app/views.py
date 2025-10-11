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

logger = logging.getLogger(__name__)


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


# Chat Views
class ChatView(LoginRequiredMixin, View):
    """Chat interface view"""
    template_name = 'rag_app/chat.html'
    
    def get(self, request, session_id=None):
        """Handle GET requests - show chat interface"""
        user = request.user
        
        # Check if a subject parameter is provided for starting a new subject chat
        subject_id = request.GET.get('subject')
        
        # Get or create chat session
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=user)
        elif subject_id:
            # Create a new chat session for the specified subject
            try:
                subject = get_object_or_404(Subject, id=subject_id, created_by=user)
                
                # Check if the subject has any processed documents
                has_documents = Document.objects.filter(
                    subject=subject, 
                    processed=True
                ).exists()
                
                if not has_documents:
                    messages.warning(
                        request, 
                        f'No processed documents found in "{subject.name}". Please upload and process some documents first.'
                    )
                    return redirect('rag_app:subject_detail', pk=subject.id)
                
                session = ChatSession.objects.create(
                    user=user,
                    subject=subject,
                    title=f"Chat with {subject.name}",
                    chat_type='subject'
                )
                # Redirect to the new session to avoid confusion with URL parameters
                return redirect('rag_app:chat_session', session_id=session.id)
            except (Subject.DoesNotExist, ValueError):
                # If subject doesn't exist or invalid ID, fall back to general chat
                session = ChatSession.objects.filter(user=user).order_by('-last_activity').first()
                if not session:
                    session = ChatSession.objects.create(user=user, title="New Chat")
        else:
            session = ChatSession.objects.filter(user=user).order_by('-last_activity').first()
            if not session:
                session = ChatSession.objects.create(user=user, title="New Chat")
        
        context = {
            'session': session,
            'current_session': session,  # For template compatibility
            'messages': session.messages.all() if session else [],
            'chat_sessions': ChatSession.objects.filter(user=user).order_by('-last_activity')[:10],
            'recent_sessions': ChatSession.objects.filter(user=user).order_by('-last_activity')[:10],
            'subjects': Subject.objects.filter(created_by=user),
            'user_documents': Document.objects.filter(uploaded_by=user, processed=True).order_by('-uploaded_at'),
            'user_subjects': Subject.objects.filter(created_by=user).annotate(
                document_count=Count('documents', filter=Q(documents__processed=True))
            ).filter(document_count__gt=0),
            'form': ChatMessageForm(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, session_id=None):
        """Handle POST requests - send message"""
        try:
            user = request.user
            message_text = request.POST.get('message', '').strip()
            
            if not message_text:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Get or create session
            if session_id:
                session = get_object_or_404(ChatSession, id=session_id, user=user)
            else:
                # Get the most recent session for this user or create a new one
                session = ChatSession.objects.filter(user=user).order_by('-last_activity').first()
                if not session:
                    session = ChatSession.objects.create(
                        user=user,
                        title=message_text[:50] + "..." if len(message_text) > 50 else message_text
                    )
                else:
                    # Update the session title if it's still "New Chat" and this is the first user message
                    if session.title == "New Chat" and not session.messages.filter(is_user=True).exists():
                        session.title = message_text[:50] + "..." if len(message_text) > 50 else message_text
                        session.save()
            
            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                message=message_text,
                is_user=True
            )
            
            # Generate AI response using RAG pipeline
            start_time = timezone.now()
            
            try:
                # Import RAG model
                
                
                # Get RAG model instance
                rag_model = get_rag_model()
                
                # Check if user has any documents before allowing chat
                user_has_documents = Document.objects.filter(uploaded_by=user).exists()
                user_has_subjects_with_docs = Subject.objects.filter(
                    created_by=user, documents__isnull=False
                ).exists()
                
                # Process query based on session type
                if session.chat_type == 'anonymous' and session.temp_document:
                    # Anonymous document chat
                    rag_result = rag_model.query_temp_document(
                        question=message_text,
                        temp_document=session.temp_document,
                        chat_session=session
                    )
                elif session.document:
                    # Specific document chat (stored document)
                    rag_result = rag_model.query(
                        question=message_text,
                        document_id=session.document.id,
                        chat_session=session,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                elif session.subject:
                    # Subject-based chat with all documents from the subject
                    subject_has_docs = Document.objects.filter(subject=session.subject).exists()
                    if not subject_has_docs:
                        ai_response = f"No documents have been uploaded to the '{session.subject.name}' subject yet. Please upload some documents to this subject before starting a chat."
                    else:
                        rag_result = rag_model.query(
                            question=message_text,
                            subject_id=session.subject.id,
                            chat_session=session,
                            retrieval_strategy='hybrid',
                            max_chunks=5
                        )
                elif user_has_documents or user_has_subjects_with_docs:
                    # General chat with user's documents
                    rag_result = rag_model.query(
                        question=message_text,
                        subject_id=None,
                        chat_session=session,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                else:
                    # No documents available - provide helpful guidance
                    ai_response = """Hello! I'm your AI study assistant. To get started, you'll need to upload some documents first. Here's how:

1. **Create a Subject**: Go to the Subjects section and create a new subject for your study material
2. **Upload Documents**: Add PDF, Word, PowerPoint, or text files to your subject
3. **Start Chatting**: Once documents are uploaded and processed, you can ask me questions about them

Alternatively, you can use the "Chat with Document" feature to quickly upload a single document and start chatting about it immediately.

What would you like to do first?"""
                
                # Only process RAG result if we didn't set a custom response
                if 'ai_response' not in locals() and 'rag_result' in locals():
                    if rag_result['success']:
                        ai_response = rag_result['answer']
                    else:
                        ai_response = rag_result.get('answer', 'I apologize, but I encountered an error while processing your question.')
                        logger.warning(f"RAG query failed: {rag_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error using RAG model: {e}")
                # Fallback to simple response
                ai_response = "I'm having trouble accessing the document knowledge base right now. Please make sure documents are uploaded and try again."
            response_time = (timezone.now() - start_time).total_seconds()
            
            # Save AI message
            ai_message = ChatMessage.objects.create(
                session=session,
                message=ai_response,
                is_user=False,
                response_time=response_time
            )
            
            # Update session activity
            session.last_activity = timezone.now()
            session.save()
            
            return JsonResponse({
                'success': True,
                'response': ai_response,
                'session_id': str(session.id),
                'ai_message': {
                    'id': str(ai_message.id),
                    'message': ai_message.message,
                    'timestamp': ai_message.timestamp.isoformat(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error in chat POST: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your message'}, status=500)


@login_required
@csrf_exempt
def send_message(request):
    """Send chat message via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
            session_id = data.get('session_id')
            subject_id = data.get('subject_id')
            
            if not message_text:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Get or create session
            if session_id:
                session = get_object_or_404(ChatSession, id=session_id, user=request.user)
            else:
                # Get the most recent session for this user or create a new one
                session = ChatSession.objects.filter(user=request.user).order_by('-last_activity').first()
                if not session:
                    session = ChatSession.objects.create(
                        user=request.user,
                        title=message_text[:50] + "..." if len(message_text) > 50 else message_text,
                        subject_id=subject_id if subject_id else None
                    )
                else:
                    # Update the session title if it's still "New Chat" and this is the first user message
                    if session.title == "New Chat" and not session.messages.filter(is_user=True).exists():
                        session.title = message_text[:50] + "..." if len(message_text) > 50 else message_text
                        session.save()
            
            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                message=message_text,
                is_user=True
            )
            
            # Generate AI response using RAG pipeline
            start_time = timezone.now()
            
            try:
                # Import RAG model
                from .pipeline.model import get_rag_model
                
                # Get RAG model instance
                rag_model = get_rag_model()
                
                # Check if user has any documents before allowing chat
                user_has_documents = Document.objects.filter(uploaded_by=request.user).exists()
                user_has_subjects_with_docs = Subject.objects.filter(
                    created_by=request.user, documents__isnull=False
                ).exists()
                
                # Process query based on session type
                if session.chat_type == 'anonymous' and session.temp_document:
                    # Anonymous document chat
                    rag_result = rag_model.query_temp_document(
                        question=message_text,
                        temp_document=session.temp_document,
                        chat_session=session
                    )
                elif session.chat_type == 'document' and session.document:
                    # Specific document chat (for stored documents)
                    if not session.document.processed:
                        ai_response = f"The document '{session.document.title}' is still being processed. Please wait a moment and try again."
                    else:
                        rag_result = rag_model.query(
                            question=message_text,
                            document_id=session.document.id,
                            chat_session=session,
                            retrieval_strategy='hybrid',
                            max_chunks=5
                        )
                elif session.document:
                    # Session has a document but chat_type is not 'document' - still filter by document
                    rag_result = rag_model.query(
                        question=message_text,
                        document_id=session.document.id,
                        chat_session=session,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                elif session.subject:
                    # Subject-based chat with all documents from the subject
                    subject_has_docs = Document.objects.filter(subject=session.subject).exists()
                    if not subject_has_docs:
                        ai_response = f"No documents have been uploaded to the '{session.subject.name}' subject yet. Please upload some documents to this subject before starting a chat."
                    else:
                        rag_result = rag_model.query(
                            question=message_text,
                            subject_id=session.subject.id,
                            chat_session=session,
                            retrieval_strategy='hybrid',
                            max_chunks=5
                        )
                elif user_has_documents or user_has_subjects_with_docs:
                    # General chat with user's documents
                    rag_result = rag_model.query(
                        question=message_text,
                        subject_id=None,
                        chat_session=session,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                else:
                    # No documents available - provide helpful guidance
                    ai_response = """Hello! I'm your AI study assistant. To get started, you'll need to upload some documents first. Here's how:

1. **Create a Subject**: Go to the Subjects section and create a new subject for your study material
2. **Upload Documents**: Add PDF, Word, PowerPoint, or text files to your subject
3. **Start Chatting**: Once documents are uploaded and processed, you can ask me questions about them

Alternatively, you can use the "Chat with Document" feature to quickly upload a single document and start chatting about it immediately.

What would you like to do first?"""
                
                # Only process RAG result if we didn't set a custom response
                if 'ai_response' not in locals() and 'rag_result' in locals():
                    if rag_result['success']:
                        ai_response = rag_result['answer']
                        
                        # Store relevant chunks for this message
                        if rag_result.get('sources'):
                            chunk_ids = [chunk['chunk_id'] for chunk in rag_result['sources']]
                            # Note: Will link chunks after saving the message
                    else:
                        ai_response = rag_result.get('answer', 'I apologize, but I encountered an error while processing your question.')
                        logger.warning(f"RAG query failed: {rag_result.get('error')}")
                
                # Clean the AI response to remove thinking tags
                ai_response = clean_ai_response(ai_response)
                    
            except Exception as e:
                logger.error(f"Error using RAG model: {e}")
                # Fallback to simple response
                ai_response = "I'm having trouble accessing the document knowledge base right now. Please make sure documents are uploaded and try again."
            
            response_time = (timezone.now() - start_time).total_seconds()
            
            # Save AI message
            ai_message = ChatMessage.objects.create(
                session=session,
                message=ai_response,
                is_user=False,
                response_time=response_time
            )
            
            # Link relevant chunks if available
            try:
                if 'rag_result' in locals() and rag_result.get('success') and rag_result.get('sources'):
                    chunk_ids = [chunk['chunk_id'] for chunk in rag_result['sources']]
                    chunks = DocumentChunk.objects.filter(id__in=chunk_ids)
                    ai_message.relevant_chunks.set(chunks)
            except Exception as e:
                logger.warning(f"Error linking chunks to message: {e}")
            
            # Update session activity
            session.last_activity = timezone.now()
            session.save()
            
            # Prepare response data
            response_data = {
                'success': True,
                'session_id': str(session.id),
                'user_message': {
                    'id': str(user_message.id),
                    'message': user_message.message,
                    'timestamp': user_message.timestamp.isoformat()
                },
                'ai_message': {
                    'id': str(ai_message.id),
                    'message': ai_message.message,
                    'timestamp': ai_message.timestamp.isoformat(),
                    'response_time': response_time
                }
            }
            
            # Add source information if available
            if 'rag_result' in locals() and rag_result.get('success') and rag_result.get('sources'):
                response_data['sources'] = [
                    {
                        'document_title': chunk['document_title'],
                        'document_type': chunk['document_type'],
                        'page_number': chunk['page_number'],
                        'relevance_score': round(chunk['score'], 3)
                    }
                    for chunk in rag_result['sources'][:3]  # Limit to top 3 sources
                ]
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your message'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


class AnonymousDocumentChatView(LoginRequiredMixin, View):
    """Anonymous document chat - upload a document and chat about it"""
    template_name = 'rag_app/anonymous_chat.html'
    
    def get(self, request):
        """Show anonymous chat upload form"""
        return render(request, self.template_name)
    
    def post(self, request):
        """Handle document upload and start chat session"""
        try:
            file = request.FILES.get('file')
            initial_question = request.POST.get('initial_question', '').strip()
            processing_mode = request.POST.get('processing_mode', 'fast')
            
            if not file:
                messages.error(request, 'Please select a file to upload.')
                return render(request, self.template_name)
            
            # Validate file
            if file.size > 50 * 1024 * 1024:  # 50MB limit
                messages.error(request, 'File size must be less than 50MB.')
                return render(request, self.template_name)
            
            # Validate processing mode
            if processing_mode not in ['fast', 'ocr']:
                processing_mode = 'fast'
            
            # Create temporary document
            from django.utils import timezone
            temp_doc = TempDocument.objects.create(
                title=file.name.rsplit('.', 1)[0],  # Remove extension
                file=file,
                processing_mode=processing_mode,
                uploaded_by=request.user,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Process document immediately for chat
            try:
                from .pipeline.data_processor import DocumentProcessor
                processor = DocumentProcessor()
                
                # Show appropriate processing message
                if processing_mode == 'ocr':
                    messages.info(request, 'Processing document with advanced OCR. This may take a few minutes...')
                else:
                    messages.info(request, 'Processing document with fast mode...')
                
                # Process the temporary document (adapt processor for temp docs)
                result = processor.process_temp_document(temp_doc)
                
                if result.get('success'):
                    temp_doc.processed = True
                    temp_doc.save()
                    
                    # Show success message with processing details
                    mode_name = 'Advanced OCR' if processing_mode == 'ocr' else 'Fast'
                    processing_time = result.get('processing_time', 0)
                    
                    if processing_mode == 'ocr' and result.get('ocr_images_processed', 0) > 0:
                        messages.success(request, 
                            f'Document processed successfully with {mode_name} mode! '
                            f'Analyzed {result["ocr_images_processed"]} images with OCR in {processing_time:.1f}s.')
                    else:
                        messages.success(request, 
                            f'Document processed successfully with {mode_name} mode in {processing_time:.1f}s!')
                else:
                    raise Exception(result.get('error', 'Unknown processing error'))
                
            except Exception as e:
                logger.error(f"Error processing temp document {temp_doc.id}: {str(e)}")
                messages.error(request, 'Error processing document. Please try again.')
                return render(request, self.template_name)
            
            # Create chat session
            session_title = f"Chat about {temp_doc.title}"
            if initial_question:
                session_title = initial_question[:50] + "..." if len(initial_question) > 50 else initial_question
            
            chat_session = ChatSession.objects.create(
                user=request.user,
                temp_document=temp_doc,
                title=session_title,
                chat_type='anonymous'
            )
            
            # If there's an initial question, process it
            if initial_question:
                try:
                    # Save user message
                    user_message = ChatMessage.objects.create(
                        session=chat_session,
                        message=initial_question,
                        is_user=True
                    )
                    
                    # Generate AI response
                    from .pipeline.model import get_rag_model
                    rag_model = get_rag_model()
                    
                    # Process query with temp document
                    rag_result = rag_model.query_temp_document(
                        question=initial_question,
                        temp_document=temp_doc,
                        chat_session=chat_session
                    )
                    
                    if rag_result['success']:
                        ai_response = rag_result['answer']
                    else:
                        ai_response = "I've processed your document. What would you like to know about it?"
                    
                    # Save AI message
                    ChatMessage.objects.create(
                        session=chat_session,
                        message=ai_response,
                        is_user=False
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing initial question: {str(e)}")
                    # Continue without the initial response
            
            # Redirect to chat session
            messages.success(request, 'Document uploaded successfully! You can now chat about it.')
            return redirect('rag_app:chat_session', session_id=chat_session.id)
            
        except Exception as e:
            logger.error(f"Error in anonymous chat upload: {str(e)}")
            messages.error(request, 'An error occurred while processing your document.')
            return render(request, self.template_name)


@login_required
def new_chat_session(request):
    """Create new chat session"""
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        session = ChatSession.objects.create(
            user=request.user,
            title="New Chat",
            subject_id=subject_id if subject_id else None
        )
        return redirect('rag_app:chat_session', session_id=session.id)
    
    return redirect('rag_app:chat')


@login_required
@csrf_exempt
def stream_chat_response(request, session_id=None):
    """Stream chat response using Server-Sent Events"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        user = request.user
        
        # Get or create session
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, user=user)
        else:
            session = ChatSession.objects.filter(user=user).order_by('-last_activity').first()
            if not session:
                session = ChatSession.objects.create(
                    user=user,
                    title=message_text[:50] + "..." if len(message_text) > 50 else message_text
                )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message=message_text,
            is_user=True
        )
        
        # Create a proper streaming response
        def event_stream():
            try:
                yield "data: " + json.dumps({"type": "start"}) + "\n\n"
                
                # Import RAG model
                from .pipeline.model import get_rag_model
                rag_model = get_rag_model()
                
                # Check if user has any documents before allowing chat
                user_has_documents = Document.objects.filter(uploaded_by=user).exists()
                user_has_subjects_with_docs = Subject.objects.filter(
                    created_by=user, documents__isnull=False
                ).exists()
                
                # Build context and messages
                if session.chat_type == 'anonymous' and session.temp_document:
                    # Get document content for temp documents
                    from django.core.cache import cache
                    cache_key = f"temp_doc_content_{session.temp_document.id}"
                    document_content = cache.get(cache_key)
                    
                    if not document_content:
                        from .pipeline.data_processor import DocumentProcessor
                        processor = DocumentProcessor()
                        document_content = processor._extract_temp_document_text(session.temp_document)
                        cache.set(cache_key, document_content, timeout=86400)
                    
                    context = f"Document: {session.temp_document.title}\n\n{document_content[:8000]}"
                    subject_id = None
                    document_id = None
                    
                elif session.document:
                    # Get retrieval context for specific document
                    retrieval_result = rag_model.retriever.retrieve_for_query(
                        query=message_text,
                        document_id=session.document.id,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                    context = retrieval_result.get('context', '') if retrieval_result['success'] else ''
                    subject_id = None
                    document_id = session.document.id
                    
                elif session.subject:
                    # Get retrieval context for subject
                    retrieval_result = rag_model.retriever.retrieve_for_query(
                        query=message_text,
                        subject_id=session.subject.id,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                    context = retrieval_result.get('context', '') if retrieval_result['success'] else ''
                    subject_id = session.subject.id
                    document_id = None
                    
                elif user_has_documents or user_has_subjects_with_docs:
                    # Get general retrieval context
                    retrieval_result = rag_model.retriever.retrieve_for_query(
                        query=message_text,
                        subject_id=None,
                        retrieval_strategy='hybrid',
                        max_chunks=5
                    )
                    context = retrieval_result.get('context', '') if retrieval_result['success'] else ''
                    subject_id = None
                    document_id = None
                    
                else:
                    # No documents - provide guidance
                    full_response = """Hello! I'm your AI study assistant. To get started, you'll need to upload some documents first. Here's how:

1. **Create a Subject**: Go to the Subjects section and create a new subject for your study material
2. **Upload Documents**: Add PDF, Word, PowerPoint, or text files to your subject  
3. **Start Chatting**: Once documents are uploaded and processed, you can ask me questions about them

What would you like to do first?"""
                    
                    # Stream the response word by word
                    words = full_response.split(' ')
                    for i, word in enumerate(words):
                        if i == 0:
                            chunk = word
                        else:
                            chunk = ' ' + word
                        yield "data: " + json.dumps({"type": "chunk", "content": chunk}) + "\n\n"
                        
                    # Save message and complete
                    ai_message = ChatMessage.objects.create(
                        session=session,
                        message=full_response,
                        is_user=False
                    )
                    session.last_activity = timezone.now()
                    session.save()
                    
                    yield "data: " + json.dumps({
                        "type": "complete", 
                        "session_id": str(session.id),
                        "message_id": str(ai_message.id)
                    }) + "\n\n"
                    return
                
                # Build messages for LLM
                messages = rag_model._build_chat_messages(
                    question=message_text,
                    context=context,
                    chat_session=session,
                    subject_id=subject_id
                )
                
                # Stream the LLM response
                full_response = ""
                
                # We need to handle streaming differently since we're in a generator
                # Let's create a custom streaming approach
                import requests
                import sseclient
                
                start_time = timezone.now()
                payload = {
                    "model": rag_model.llm_model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "top_p": 0.9,
                    "stream": True
                }
                
                # Send streaming request directly
                api_response = requests.post(
                    rag_model.api_url,
                    headers=rag_model.headers,
                    json=payload,
                    timeout=60,
                    stream=True
                )
                
                if api_response.status_code == 200:
                    client = sseclient.SSEClient(api_response)
                    think_filter = ThinkTagFilter()  # Initialize the filter
                    
                    for event in client.events():
                        if event.data == "[DONE]":
                            break
                            
                        if event.data:
                            try:
                                chunk_data = json.loads(event.data)
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        chunk = delta["content"]
                                        full_response += chunk
                                        
                                        # Filter out think tags from the chunk before streaming
                                        filtered_chunk = think_filter.filter_chunk(chunk)
                                        if filtered_chunk:  # Only stream if there's content after filtering
                                            yield "data: " + json.dumps({"type": "chunk", "content": filtered_chunk}) + "\n\n"
                                        
                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                continue
                    
                    result = {'success': True, 'response_time': (timezone.now() - start_time).total_seconds()}
                else:
                    result = {'success': False, 'error': f'API error: {api_response.status_code}'}
                
                if result['success'] and full_response:
                    # Clean the response to remove thinking tags
                    cleaned_response = clean_ai_response(full_response)
                    
                    # Save AI message
                    ai_message = ChatMessage.objects.create(
                        session=session,
                        message=cleaned_response,
                        is_user=False,
                        response_time=result.get('response_time', 0)
                    )
                    
                    # Update session
                    session.last_activity = timezone.now()
                    session.save()
                    
                    yield "data: " + json.dumps({
                        "type": "complete",
                        "session_id": str(session.id), 
                        "message_id": str(ai_message.id)
                    }) + "\n\n"
                else:
                    yield "data: " + json.dumps({
                        "type": "error", 
                        "error": result.get('error', 'Unknown error')
                    }) + "\n\n"
                    
            except Exception as e:
                logger.error(f"Error in streaming: {e}")
                yield "data: " + json.dumps({"type": "error", "error": str(e)}) + "\n\n"
        
        # Create streaming response without problematic headers
        from django.http import StreamingHttpResponse
        response = StreamingHttpResponse(event_stream(), content_type='text/plain')
        response['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        logger.error(f"Error setting up streaming chat: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def chat_with_subject(request):
    """Chat with documents from a specific subject"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_text = data.get('message', '').strip()
            subject_id = data.get('subject_id')
            session_id = data.get('session_id')
            
            if not message_text:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            if not subject_id:
                return JsonResponse({'error': 'Subject ID is required'}, status=400)
            
            # Verify user has access to the subject
            try:
                subject = Subject.objects.get(id=subject_id, created_by=request.user)
            except Subject.DoesNotExist:
                return JsonResponse({'error': 'Subject not found or access denied'}, status=403)
            
            # Get or create session
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id, user=request.user, subject_id=subject_id)
                except ChatSession.DoesNotExist:
                    return JsonResponse({'error': 'Chat session not found'}, status=404)
            else:
                session = ChatSession.objects.create(
                    user=request.user,
                    subject=subject,
                    title=f"{subject.name}: {message_text[:30]}..." if len(message_text) > 30 else f"{subject.name}: {message_text}"
                )
            
            # Save user message
            user_message = ChatMessage.objects.create(
                session=session,
                message=message_text,
                is_user=True
            )
            
            # Generate AI response using RAG pipeline with subject filtering
            start_time = timezone.now()
            
            try:
                from .pipeline.model import get_rag_model
                
                rag_model = get_rag_model()
                
                # Use chat_with_subject method for better subject integration
                rag_result = rag_model.chat_with_subject(
                    question=message_text,
                    subject_id=subject_id,
                    chat_session=session
                )
                
                if rag_result['success']:
                    ai_response = rag_result['answer']
                    sources = rag_result.get('sources', [])
                else:
                    ai_response = rag_result.get('answer', f'I apologize, but I couldn\'t find relevant information in the {subject.name} documents to answer your question.')
                    sources = []
                    logger.warning(f"RAG query failed for subject {subject_id}: {rag_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error using RAG model for subject {subject_id}: {e}")
                ai_response = f"I'm having trouble accessing the {subject.name} documents right now. Please make sure documents are uploaded for this subject and try again."
                sources = []
            
            response_time = (timezone.now() - start_time).total_seconds()
            
            # Save AI message
            ai_message = ChatMessage.objects.create(
                session=session,
                message=ai_response,
                is_user=False,
                response_time=response_time
            )
            
            # Link relevant chunks if available
            try:
                if sources:
                    chunk_ids = [chunk['chunk_id'] for chunk in sources]
                    chunks = DocumentChunk.objects.filter(id__in=chunk_ids)
                    ai_message.relevant_chunks.set(chunks)
            except Exception as e:
                logger.warning(f"Error linking chunks to message: {e}")
            
            # Update session activity
            session.last_activity = timezone.now()
            session.save()
            
            # Prepare response
            response_data = {
                'success': True,
                'session_id': str(session.id),
                'subject': {
                    'id': subject.id,
                    'name': subject.name,
                    'code': subject.code
                },
                'user_message': {
                    'id': str(user_message.id),
                    'message': user_message.message,
                    'timestamp': user_message.timestamp.isoformat()
                },
                'ai_message': {
                    'id': str(ai_message.id),
                    'message': ai_message.message,
                    'timestamp': ai_message.timestamp.isoformat(),
                    'response_time': response_time
                }
            }
            
            # Add source information
            if sources:
                response_data['sources'] = [
                    {
                        'document_title': chunk['document_title'],
                        'document_type': chunk['document_type'],
                        'page_number': chunk['page_number'],
                        'relevance_score': round(chunk['score'], 3)
                    }
                    for chunk in sources[:5]  # Limit to top 5 sources
                ]
                response_data['documents_used'] = len(set(chunk['document_id'] for chunk in sources))
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error in subject chat: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing your message'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def get_subject_documents(request, subject_id):
    """Get documents available for a subject"""
    try:
        subject = Subject.objects.get(id=subject_id, created_by=request.user)
        documents = Document.objects.filter(
            subject=subject,
            processed=True
        ).values('id', 'title', 'document_type', 'page_count', 'uploaded_at')
        
        return JsonResponse({
            'success': True,
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code
            },
            'documents': list(documents),
            'total_documents': len(documents)
        })
        
    except Subject.DoesNotExist:
        return JsonResponse({'error': 'Subject not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting subject documents: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


@login_required  
def get_slide_generation_data(request):
    """Get subjects and documents for slide generation"""
    try:
        subjects = Subject.objects.filter(created_by=request.user).prefetch_related('documents')
        documents = Document.objects.filter(
            uploaded_by=request.user, 
            processed=True
        ).select_related('subject')
        
        subjects_data = []
        for subject in subjects:
            subjects_data.append({
                'id': subject.id,
                'name': subject.name,
                'code': subject.code,
                'description': subject.description,
                'document_count': subject.documents.filter(processed=True).count()
            })
        
        documents_data = []
        for doc in documents:
            documents_data.append({
                'id': str(doc.id),
                'title': doc.title,
                'document_type': doc.document_type,
                'subject_name': doc.subject.name if doc.subject else 'No Subject',
                'page_count': doc.page_count,
                'uploaded_at': doc.uploaded_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'subjects': subjects_data,
            'documents': documents_data
        })
        
    except Exception as e:
        logger.error(f"Error getting slide generation data: {e}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


# Quiz Views
"""
Simplified quiz views that only show Google Forms quiz metadata and links.
No quiz content is stored in the database - only tracking information.
"""

class QuizListView(LoginRequiredMixin, ListView):
    """List all Google Forms quizzes created by the user"""
    model = Quiz
    template_name = 'rag_app/quiz_list.html'
    context_object_name = 'quizzes'
    paginate_by = 12
    
    def get_queryset(self):
        return Quiz.objects.filter(
            created_by=self.request.user,
            google_form_url__isnull=False  # Only show quizzes with Google Form links
        ).order_by('-created_at')





@login_required
def get_quiz_questions(request, pk):
    """AJAX endpoint to get quiz questions data"""
    try:
        quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
        
        # Build questions data structure
        questions_data = []
        for question in quiz.questions.all().order_by('order'):
            choices_data = []
            for choice in question.choices.all().order_by('order'):
                choices_data.append({
                    'text': choice.choice_text,
                    'is_correct': choice.is_correct
                })
            
            questions_data.append({
                'question': question.question_text,
                'choices': choices_data,
                'explanation': question.explanation
            })
        
        return JsonResponse({
            'success': True,
            'questions': questions_data,
            'google_form_url': quiz.google_form_url,
            'google_form_edit_url': quiz.google_form_edit_url
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


"""
The submit_quiz_attempt function has been removed as part of simplifying 
the quiz functionality to only support Google Forms directly.
"""


"""
The generate_quiz_questions function has been removed as part of simplifying 
the quiz functionality to only support Google Forms directly.
"""


@login_required
def generate_rag_quiz(request):
    """Generate a new quiz using RAG and export to Google Forms"""
    if request.method == 'POST':
        try:
            # Get form data
            subject_id = request.POST.get('subject_id')
            num_questions = int(request.POST.get('num_questions', 10))
            topics = request.POST.getlist('topics')  # Optional specific topics
            title = request.POST.get('title', '')
            
            if not subject_id:
                return JsonResponse({'error': 'Subject is required'}, status=400)
            
            # Validate number of questions
            num_questions = min(max(1, num_questions), 15)
            
            # Generate quiz using QuizGenerator and create a Google Form
            from .pipeline.quiz_generator import QuizGenerator
            generator = QuizGenerator()
            logger.info(f"QuizGenerator instantiated: {type(generator)}")
            logger.info(f"QuizGenerator attributes: {dir(generator)}")
            
            result = generator.generate_quiz(
                subject_id=subject_id,
                num_questions=num_questions,
                specific_topics=topics if topics else None,
                new_owner_email=request.user.email if request.user and request.user.email else None
            )
            
            if not result['success']:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', 'Failed to generate quiz')
                }, status=500)
            
            # Save quiz metadata to database for tracking
            quiz = None
            try:
                subject = Subject.objects.get(id=subject_id)
                quiz_title = title or f"Quiz on {result['metadata']['subject']}"
                
                quiz = Quiz.objects.create(
                    title=quiz_title,
                    subject=subject,
                    created_by=request.user,
                    description=f"Auto-generated quiz covering , {', '.join(result['metadata']['topics'])}" if result['metadata']['topics'] != [''] else f"Auto-generated quiz covering {result['metadata']['subject']}",
                    total_questions=result['metadata']['num_questions'],
                    google_form_url=result.get('google_form_url'),
                    google_form_edit_url=result.get('google_form_edit_url'),
                    google_form_owner_email=request.user.email if request.user and request.user.email else None
                )
                
                # Save questions and choices to the database
                for question_data in result['questions']:
                    question = Question.objects.create(
                        quiz=quiz,
                        question_text=question_data['question'],
                        question_type=QuizType.MULTIPLE_CHOICE,  # Using the proper constant
                        explanation=question_data.get('explanation', ''),
                        order=len(quiz.questions.all()) + 1
                    )
                    
                    # Save answer choices
                    for choice_data in question_data['choices']:
                        AnswerChoice.objects.create(
                            question=question,
                            choice_text=choice_data['text'],
                            is_correct=choice_data['is_correct'],
                            order=len(question.choices.all()) + 1
                        )
                        
            except Exception as e:
                logger.warning(f"Failed to save quiz metadata: {str(e)}")
                # Continue even if we can't save to database
            
            # Persist last generation info in session for display on GET page
            try:
                request.session['last_generated_quiz'] = {
                    'success': True,
                    'quiz_id': str(quiz.id) if quiz else None,
                    'questions': result['questions'],
                    'metadata': result['metadata'],
                    'google_form_url': result.get('google_form_url'),
                    'google_form_edit_url': result.get('google_form_edit_url'),
                    'ownership_transfer': result.get('ownership_transfer')
                }
            except Exception:
                pass

            # Return results
            return JsonResponse({
                'success': True,
                'quiz_id': str(quiz.id) if quiz else None,
                'questions': result['questions'],
                'metadata': result['metadata'],
                'google_form_url': result.get('google_form_url'),
                'google_form_edit_url': result.get('google_form_edit_url'),
                'ownership_transfer': result.get('ownership_transfer')
            })
            
        except Exception as e:
            logger.error(f"Error in generate_rag_quiz: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # GET request - show form and any last generated result
    context = {
        'subjects': Subject.objects.filter(created_by=request.user),
        'last_generated_quiz': request.session.get('last_generated_quiz')
    }
    return render(request, 'rag_app/quiz_generate.html', context)





# Profile Views
class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    model = UserProfile
    template_name = 'rag_app/profile.html'
    context_object_name = 'profile'
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile"""
    model = UserProfile
    form_class = UserProfileForm
    template_name = 'rag_app/profile_edit.html'
    success_url = reverse_lazy('rag_app:profile')
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


# Slide Generation View
class SlideGenerationView(LoginRequiredMixin, TemplateView):
    """Generate slides from documents"""
    template_name = 'rag_app/slide_generate.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(created_by=self.request.user)
        context['documents'] = Document.objects.filter(
            uploaded_by=self.request.user, processed=True
        )
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            document_id = request.POST.get('document_id')
            topic = request.POST.get('topic', '')
            slide_count = int(request.POST.get('slide_count', 10))
            
            document = get_object_or_404(
                Document, id=document_id, uploaded_by=request.user
            )
            
            from .pipeline.model import SlideGenerator
            generator = SlideGenerator()
            slides = generator.generate_slides(document, topic, slide_count)
            
            return JsonResponse({
                'success': True,
                'slides': slides
            })
            
        except Exception as e:
            logger.error(f"Error generating slides: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error generating slides. Please try again.'
            })


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


# Slide Generator Views
class SlideDownloadView(LoginRequiredMixin, View):
    """Secure view for downloading generated PowerPoint files"""
    
    def get(self, request, filename):
        """Serve the PowerPoint file for download"""
        try:
            # Security check: only allow files the user owns or created
            # Extract user_id from filename (format: title_userid_timestamp.pptx)
            filename_parts = filename.replace('.pptx', '').split('_')
            if len(filename_parts) < 2:
                return HttpResponseForbidden("Invalid file access")
            
            try:
                file_user_id = int(filename_parts[-2])
                print(file_user_id)# Second to last part should be user_id
            except (ValueError, IndexError):
                return HttpResponseForbidden("Invalid file access")
            print(file_user_id)
            print(request.user.id)
            # Check if user can access this file
            # if request.user.id != file_user_id :
            #     return HttpResponseForbidden("You don't have permission to access this file")
            #
            # Construct file path
            file_path = os.path.join(settings.MEDIA_ROOT, 'generated_slides', filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise Http404("File not found")
            
            # Serve the file
            try:
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    response['Content-Length'] = os.path.getsize(file_path)
                    return response
            except IOError:
                raise Http404("File not found")
                
        except Exception as e:
            logger.error(f"Error serving slide file {filename}: {str(e)}")
            return HttpResponseServerError("Error accessing file")


class SlideGeneratorView(LoginRequiredMixin, View):
    """View for generating PowerPoint slides from uploaded documents"""
    template_name = 'rag_app/slide_generate.html'
    
    def get(self, request):
        """Render the slide generator form"""
        # Check if RAG model/LLM is available
        try:
            from .pipeline.model import RAGModel
            # Try to initialize to check if API key is configured
            rag_model = RAGModel()
            ai_available = True
        except Exception:
            ai_available = False
        
        # Get user's subjects and documents
        subjects = Subject.objects.filter(created_by=request.user).prefetch_related('documents')
        documents = Document.objects.filter(
            uploaded_by=request.user, processed=True
        ).select_related('subject')
        
        context = {
            'page_title': 'Generate Slides',
            'user': request.user,
            'ai_available': ai_available,
            'subjects': subjects,
            'documents': documents
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Process slide generation request"""
        try:
            # Get form data
            slide_count = request.POST.get('slide_count', 'auto')
            custom_slide_count = request.POST.get('custom_slide_count')
            template = request.POST.get('template', 'professional')
            title = request.POST.get('title', '')
            language = request.POST.get('language', 'en')
            instructions = request.POST.get('instructions', '')
            background_image = request.FILES.get('background_image')
            # Checkbox: if present in POST data = checked, if absent = unchecked
            include_images = request.POST.get('include_images') == 'true'
            logger.info(f"📸 Include images setting: {include_images} (raw value: {request.POST.get('include_images')})")
            
            # Get content source - either uploaded files, existing documents, or subject documents
            content_source = request.POST.get('content_source', 'upload')
            uploaded_files = request.FILES.getlist('documents')
            selected_documents = request.POST.getlist('selected_documents')
            selected_subject = request.POST.get('selected_subject')
            
            # Determine the files to process
            files_to_process = []
            
            if content_source == 'upload':
                # Use uploaded files
                if not uploaded_files:
                    return JsonResponse({
                        'success': False, 
                        'error': 'No files uploaded'
                    }, status=400)
                files_to_process = uploaded_files
                
            elif content_source == 'existing_documents':
                # Use selected existing documents
                if not selected_documents:
                    return JsonResponse({
                        'success': False, 
                        'error': 'No documents selected'
                    }, status=400)
                # Get the actual document files
                documents = Document.objects.filter(
                    id__in=selected_documents, 
                    uploaded_by=request.user,
                    processed=True
                )
                files_to_process = [doc.file for doc in documents]
                
            elif content_source == 'subject':
                # Use all documents from selected subject
                if not selected_subject:
                    return JsonResponse({
                        'success': False, 
                        'error': 'No subject selected'
                    }, status=400)
                try:
                    subject = Subject.objects.get(id=selected_subject, created_by=request.user)
                    documents = Document.objects.filter(
                        subject=subject,
                        processed=True
                    )
                    print(f"Found {documents.count()} documents for subject '{subject.name}'")
                    if not documents:
                        return JsonResponse({
                            'success': False, 
                            'error': f'No processed documents found for subject "{subject.name}"'
                        }, status=400)
                    files_to_process = [doc.file for doc in documents]
                    print("a7a")
                    print(f"Processing {len(files_to_process)} files from subject '{subject.name}': {[doc.title for doc in documents]}")
                    # Update title if not provided
                    print(title)
                    if not title:
                        title = f"{subject.name} - Presentation"
                except Subject.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Selected subject not found'
                    }, status=400)
            
            if not files_to_process:
                return JsonResponse({
                    'success': False, 
                    'error': 'No content source specified'
                }, status=400)
            
            # Validate slide count
            if slide_count == 'custom':
                try:
                    slide_count = int(custom_slide_count)
                    if slide_count < 1 or slide_count > 50:
                        raise ValueError("Slide count must be between 1 and 50")
                except (ValueError, TypeError):
                    return JsonResponse({
                        'success': False,
                        'error': 'Invalid custom slide count'
                    }, status=400)
            elif slide_count != 'auto':
                try:
                    slide_count = int(slide_count)
                except ValueError:
                    slide_count = 'auto'
            
            # Process files and generate slides
            processor = SlideProcessor()
            result = processor.generate_slides(
                files=files_to_process,
                slide_count=slide_count,
                template=template,
                title=title,
                language=language,
                instructions=instructions,
                user=request.user,
                background_image=background_image,
                documents=documents if 'documents' in locals() else None,  # Pass Document objects for image support
                include_images=include_images  # Pass image preference
            )
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': 'Slides generated successfully!',
                    'download_url': result['download_url'],
                    'file_name': result['file_name']
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result['error']
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error in slide generation: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'An error occurred while generating slides'
            }, status=500)


class SlidesListView(LoginRequiredMixin, View):
    """List all generated slides for the current user"""
    template_name = 'rag_app/slides_list.html'

    def get(self, request):
        try:
            user_id_str = f"_{request.user.id}_"
            slides_dir = os.path.join(settings.MEDIA_ROOT, 'generated_slides')
            slide_entries = []

            if os.path.isdir(slides_dir):
                for filepath in glob.glob(os.path.join(slides_dir, '*.pptx')):
                    filename = os.path.basename(filepath)
                    if user_id_str in filename:
                        try:
                            mtime = os.path.getmtime(filepath)
                            size_bytes = os.path.getsize(filepath)
                            download_url = reverse('rag_app:slide_download', kwargs={'filename': filename})
                            slide_entries.append({
                                'filename': filename,
                                'modified_ts': mtime,
                                'size_bytes': size_bytes,
                                'download_url': download_url,
                            })
                        except OSError:
                            continue

            slide_entries.sort(key=lambda x: x['modified_ts'], reverse=True)

            return render(request, self.template_name, {
                'slides': slide_entries
            })
        except Exception as e:
            logger.error(f"Error listing slides: {str(e)}")
            return render(request, self.template_name, {
                'slides': [],
                'error': 'Could not list slides.'
            })
