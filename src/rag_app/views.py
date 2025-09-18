from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, 
    UpdateView, DeleteView, FormView
)
from django.views import View
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from .models import (
    Subject, Document, DocumentChunk, ChatSession, ChatMessage,
    Quiz, Question, QuizAttempt, QuizResponse, UserProfile, StudySession,
    TempDocument
)
from .forms import (
    SubjectForm, DocumentUploadForm, QuizCreateForm, UserProfileForm,
    ChatMessageForm
)
from .pipeline.data_processor import DocumentProcessor
from .auth_backends import get_supabase_user_from_session

logger = logging.getLogger(__name__)


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
            'total_quizzes': Quiz.objects.filter(created_by=user).count(),
            'recent_documents': Document.objects.filter(uploaded_by=user).order_by('-uploaded_at')[:5],
            'recent_quizzes': Quiz.objects.filter(created_by=user).order_by('-created_at')[:5],
            'recent_chat_sessions': ChatSession.objects.filter(user=user).order_by('-last_activity')[:5],
            'quiz_attempts': QuizAttempt.objects.filter(user=user, is_completed=True).order_by('-completed_at')[:5],
        })
        
        # Calculate average quiz score
        avg_score = QuizAttempt.objects.filter(
            user=user, is_completed=True
        ).aggregate(avg_score=Avg('score'))['avg_score']
        context['average_quiz_score'] = round(avg_score, 1) if avg_score else 0
        
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
            'quizzes': subject.quizzes.all(),
            'document_count': subject.documents.count(),
            'quiz_count': subject.quizzes.count(),
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
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        return queryset.order_by('-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(created_by=self.request.user)
        context['selected_subject'] = self.request.GET.get('subject')
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
            processor.process_document(self.object)
            messages.success(self.request, 'Document uploaded and processed successfully!')
        except Exception as e:
            logger.error(f"Error processing document {self.object.id}: {str(e)}")
            messages.warning(self.request, 'Document uploaded but processing failed. Please try again.')
        
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
                from .pipeline.model import get_rag_model
                
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
            
            if not file:
                messages.error(request, 'Please select a file to upload.')
                return render(request, self.template_name)
            
            # Validate file
            if file.size > 50 * 1024 * 1024:  # 50MB limit
                messages.error(request, 'File size must be less than 50MB.')
                return render(request, self.template_name)
            
            # Create temporary document
            from django.utils import timezone
            temp_doc = TempDocument.objects.create(
                title=file.name.rsplit('.', 1)[0],  # Remove extension
                file=file,
                uploaded_by=request.user,
                expires_at=timezone.now() + timezone.timedelta(hours=24)
            )
            
            # Process document immediately for chat
            try:
                from .pipeline.data_processor import DocumentProcessor
                processor = DocumentProcessor()
                
                # Process the temporary document (adapt processor for temp docs)
                processor.process_temp_document(temp_doc)
                temp_doc.processed = True
                temp_doc.save()
                
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


# Quiz Views
class QuizListView(LoginRequiredMixin, ListView):
    """List all quizzes for the user"""
    model = Quiz
    template_name = 'rag_app/quiz_list.html'
    context_object_name = 'quizzes'
    paginate_by = 12
    
    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user).order_by('-created_at')


class QuizDetailView(LoginRequiredMixin, DetailView):
    """Quiz detail view"""
    model = Quiz
    template_name = 'rag_app/quiz_detail.html'
    context_object_name = 'quiz'
    
    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        context.update({
            'questions': quiz.questions.all(),
            'user_attempts': quiz.attempts.filter(user=self.request.user),
            'can_retake': True,  # Add logic for retake restrictions if needed
        })
        return context


class QuizCreateView(LoginRequiredMixin, CreateView):
    """Create new quiz"""
    model = Quiz
    form_class = QuizCreateForm
    template_name = 'rag_app/quiz_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Quiz created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('rag_app:quiz_detail', kwargs={'pk': self.object.pk})


class QuizTakeView(LoginRequiredMixin, DetailView):
    """Take quiz view"""
    model = Quiz
    template_name = 'rag_app/quiz_take.html'
    context_object_name = 'quiz'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quiz = self.get_object()
        
        # Create or get existing attempt
        attempt, created = QuizAttempt.objects.get_or_create(
            quiz=quiz,
            user=self.request.user,
            is_completed=False,
            defaults={'total_points': sum(q.points for q in quiz.questions.all())}
        )
        
        context.update({
            'attempt': attempt,
            'questions': quiz.questions.all(),
            'existing_responses': {
                r.question_id: r for r in attempt.responses.all()
            } if not created else {}
        })
        return context


class QuizResultsView(LoginRequiredMixin, DetailView):
    """Quiz results view"""
    model = QuizAttempt
    template_name = 'rag_app/quiz_results.html'
    context_object_name = 'attempt'
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user, is_completed=True)


class QuizAttemptDetailView(LoginRequiredMixin, DetailView):
    """Quiz attempt detail view"""
    model = QuizAttempt
    template_name = 'rag_app/quiz_attempt_detail.html'
    context_object_name = 'attempt'
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)


@login_required
def submit_quiz_attempt(request, pk):
    """Submit quiz attempt"""
    attempt = get_object_or_404(QuizAttempt, pk=pk, user=request.user, is_completed=False)
    
    if request.method == 'POST':
        try:
            # Process answers
            total_earned = 0
            for question in attempt.quiz.questions.all():
                answer_key = f'question_{question.id}'
                
                if question.question_type == 'mcq':
                    choice_id = request.POST.get(answer_key)
                    if choice_id:
                        choice = question.choices.get(id=choice_id)
                        is_correct = choice.is_correct
                        points = question.points if is_correct else 0
                        
                        QuizResponse.objects.update_or_create(
                            attempt=attempt,
                            question=question,
                            defaults={
                                'selected_choice': choice,
                                'is_correct': is_correct,
                                'points_earned': points
                            }
                        )
                        total_earned += points
                
                elif question.question_type in ['sa', 'fb']:
                    text_answer = request.POST.get(answer_key, '').strip()
                    # Simple text matching for now (can be enhanced with NLP)
                    is_correct = False  # Implement text comparison logic
                    points = question.points if is_correct else 0
                    
                    QuizResponse.objects.update_or_create(
                        attempt=attempt,
                        question=question,
                        defaults={
                            'text_answer': text_answer,
                            'is_correct': is_correct,
                            'points_earned': points
                        }
                    )
                    total_earned += points
            
            # Update attempt
            attempt.earned_points = total_earned
            attempt.completed_at = timezone.now()
            attempt.time_taken = attempt.completed_at - attempt.started_at
            attempt.is_completed = True
            attempt.calculate_score()
            
            messages.success(request, f'Quiz completed! Your score: {attempt.score:.1f}%')
            return redirect('rag_app:quiz_results', pk=attempt.pk)
            
        except Exception as e:
            logger.error(f"Error submitting quiz attempt {pk}: {str(e)}")
            messages.error(request, 'Error submitting quiz. Please try again.')
    
    return redirect('rag_app:quiz_take', pk=attempt.quiz.pk)


@login_required
def generate_quiz_questions(request, pk):
    """Generate quiz questions automatically"""
    quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
    
    try:
        from .pipeline.model import QuizGenerator
        generator = QuizGenerator()
        
        if quiz.based_on_document:
            questions = generator.generate_questions_from_document(
                quiz.based_on_document, 
                num_questions=quiz.total_questions
            )
        else:
            # Generate from all documents in subject
            documents = quiz.subject.documents.filter(processed=True)
            questions = generator.generate_questions_from_documents(
                list(documents), 
                num_questions=quiz.total_questions
            )
        
        # Save generated questions
        for i, q_data in enumerate(questions, 1):
            question = Question.objects.create(
                quiz=quiz,
                question_text=q_data['question'],
                question_type=q_data['type'],
                explanation=q_data.get('explanation', ''),
                order=i
            )
            
            # Add choices for MCQ
            if q_data['type'] == 'mcq' and 'choices' in q_data:
                for j, choice_data in enumerate(q_data['choices'], 1):
                    question.choices.create(
                        choice_text=choice_data['text'],
                        is_correct=choice_data['is_correct'],
                        order=j
                    )
        
        messages.success(request, f'Generated {len(questions)} questions successfully!')
        
    except Exception as e:
        logger.error(f"Error generating quiz questions for {pk}: {str(e)}")
        messages.error(request, 'Error generating questions. Please try again.')
    
    return redirect('rag_app:quiz_detail', pk=pk)


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


# Study Session Views
class StudySessionListView(LoginRequiredMixin, ListView):
    """List study sessions"""
    model = StudySession
    template_name = 'rag_app/study_session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        return StudySession.objects.filter(user=self.request.user)


class StudySessionDetailView(LoginRequiredMixin, DetailView):
    """Study session detail"""
    model = StudySession
    template_name = 'rag_app/study_session_detail.html'
    context_object_name = 'session'
    
    def get_queryset(self):
        return StudySession.objects.filter(user=self.request.user)


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
