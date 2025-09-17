"""
API URL patterns for EduMentorAI
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'subjects', api_views.SubjectViewSet)
router.register(r'documents', api_views.DocumentViewSet)
router.register(r'quizzes', api_views.QuizViewSet)
router.register(r'chat-sessions', api_views.ChatSessionViewSet)
router.register(r'quiz-attempts', api_views.QuizAttemptViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('chat/send-message/', api_views.SendChatMessageAPIView.as_view(), name='api_chat_send'),
    path('documents/<uuid:pk>/process/', api_views.ProcessDocumentAPIView.as_view(), name='api_document_process'),
    path('quizzes/<uuid:pk>/generate-questions/', api_views.GenerateQuizQuestionsAPIView.as_view(), name='api_quiz_generate'),
    path('search/', api_views.DocumentSearchAPIView.as_view(), name='api_search'),
    path('analytics/dashboard/', api_views.DashboardAnalyticsAPIView.as_view(), name='api_analytics'),
]
