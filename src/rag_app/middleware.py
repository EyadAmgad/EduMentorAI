"""
Custom middleware for Supabase authentication
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import login, logout
from django.contrib.auth.models import AnonymousUser
from .auth_backends import SupabaseUser, get_supabase_user_from_session
import logging

logger = logging.getLogger(__name__)


class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle Supabase authentication state
    """
    
    def process_request(self, request):
        """
        Process each request to ensure proper authentication state
        """
        # Check if we have a Supabase session
        if hasattr(request, 'session'):
            supabase_user_id = request.session.get('supabase_user_id')
            
            if supabase_user_id:
                # Try to get the current Supabase user
                supabase_user = get_supabase_user_from_session(request)
                
                if not supabase_user.is_anonymous:
                    # User is authenticated in Supabase, make sure Django knows
                    if not hasattr(request, 'user') or request.user.is_anonymous:
                        request.user = supabase_user
                else:
                    # Session exists but user is not valid, clear it
                    self._clear_supabase_session(request)
            else:
                # No Supabase session, ensure user is anonymous
                if not hasattr(request, 'user'):
                    request.user = AnonymousUser()
    
    def _clear_supabase_session(self, request):
        """
        Clear Supabase session data
        """
        keys_to_remove = ['supabase_session', 'supabase_user_id', 'supabase_user_email']
        for key in keys_to_remove:
            if key in request.session:
                del request.session[key]
