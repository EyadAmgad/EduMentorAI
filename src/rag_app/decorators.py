"""
Custom decorators and mixins for Supabase authentication
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as DjangoLoginRequiredMixin
from .auth_backends import get_supabase_user_from_session


def supabase_login_required(view_func):
    """
    Decorator for views that require Supabase authentication
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        user = get_supabase_user_from_session(request)
        if user.is_anonymous:
            messages.info(request, 'Please log in to access this page.')
            return redirect('rag_app:login')
        
        # Attach user to request for easy access
        request.supabase_user = user
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


class SupabaseLoginRequiredMixin(DjangoLoginRequiredMixin):
    """
    Mixin for class-based views that require Supabase authentication
    """
    login_url = '/login/'
    
    def dispatch(self, request, *args, **kwargs):
        user = get_supabase_user_from_session(request)
        if user.is_anonymous:
            messages.info(request, 'Please log in to access this page.')
            return redirect('rag_app:login')
        
        # Attach user to request for easy access
        request.supabase_user = user
        return super().dispatch(request, *args, **kwargs)


def get_user_identifier(user):
    """
    Get a unique identifier for the user that can be used in model ForeignKey fields
    """
    if hasattr(user, 'id'):
        return user.id
    elif hasattr(user, 'email'):
        return user.email
    return None
