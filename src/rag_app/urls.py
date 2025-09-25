"""
URL patterns for the EduMentorAI app
"""
from django.urls import path
from . import views

app_name = 'rag_app'

urlpatterns = [
    # Main pages
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Subject management
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/create/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    
    # Document management
    path('documents/', views.DocumentListView.as_view(), name='document_list'),
    path('documents/upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('documents/<uuid:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('documents/<uuid:pk>/delete/', views.DocumentDeleteView.as_view(), name='document_delete'),
    path('documents/<uuid:pk>/process/', views.process_document, name='document_process'),
    
    # Chat interface
    path('chat/', views.ChatModeView.as_view(), name='chat'),
    path('chat/mode/', views.ChatModeView.as_view(), name='chat_mode'),
    path('chat/start/', views.ChatView.as_view(), name='chat_start'),
    path('chat/anonymous/', views.AnonymousDocumentChatView.as_view(), name='anonymous_chat'),
    path('chat/<uuid:session_id>/', views.ChatView.as_view(), name='chat_session'),
    path('chat/ajax/send/', views.send_message, name='chat_send'),
    path('chat/ajax/new-session/', views.new_chat_session, name='new_chat_session'),
    path('chat/ajax/subject/', views.chat_with_subject, name='chat_with_subject'),
    path('ajax/subjects/<int:subject_id>/documents/', views.get_subject_documents, name='subject_documents'),
    
    # Quiz management
    path('quizzes/', views.QuizListView.as_view(), name='quiz_list'),

    path('quizzes/<uuid:pk>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('quizzes/<uuid:pk>/take/', views.QuizTakeView.as_view(), name='quiz_take'),
    path('quizzes/<uuid:pk>/results/', views.QuizResultsView.as_view(), name='quiz_results'),
    path('quizzes/<uuid:pk>/generate/', views.generate_quiz_questions, name='quiz_generate'),
    path('quizzes/generate-from-rag/', views.generate_rag_quiz, name='generate_rag_quiz'),
    path('quizzes/generate-form-link/', views.generate_quiz_form_link, name='generate_form_link'),
    
    # Quiz attempts
    path('quiz-attempts/<uuid:pk>/', views.QuizAttemptDetailView.as_view(), name='quiz_attempt_detail'),
    path('quiz-attempts/<uuid:pk>/submit/', views.submit_quiz_attempt, name='quiz_attempt_submit'),
    
    # User profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Study sessions
    path('study-sessions/', views.StudySessionListView.as_view(), name='study_session_list'),
    path('study-sessions/<uuid:pk>/', views.StudySessionDetailView.as_view(), name='study_session_detail'),
    
    # Slide generation
    path('slides/generate/', views.SlideGeneratorView.as_view(), name='slide_generate'),
    path('slides/download/<str:filename>/', views.SlideDownloadView.as_view(), name='slide_download'),
]
