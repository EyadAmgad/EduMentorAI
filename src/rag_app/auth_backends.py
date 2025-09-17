"""
Custom authentication backend for Supabase integration
"""
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from .supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class SupabaseUser:
    """
    Custom user class that represents a Supabase user without Django User model
    """
    def __init__(self, supabase_user_data):
        self.supabase_data = supabase_user_data
        self.id = supabase_user_data.get('id')
        self.email = supabase_user_data.get('email')
        self.is_authenticated = True
        self.is_active = supabase_user_data.get('email_confirmed_at') is not None
        self.is_anonymous = False
        self.is_staff = False
        self.is_superuser = False
        
        # Extract metadata
        metadata = supabase_user_data.get('user_metadata', {})
        self.first_name = metadata.get('first_name', '')
        self.last_name = metadata.get('last_name', '')
        self.username = self.email
        
        # Profile data
        self.full_name = f"{self.first_name} {self.last_name}".strip()
        if not self.full_name:
            self.full_name = self.email.split('@')[0]
    
    def get_full_name(self):
        return self.full_name
    
    def get_short_name(self):
        return self.first_name or self.email.split('@')[0]
    
    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        return False
    
    def has_perms(self, perm_list, obj=None):
        return False
    
    def has_module_perms(self, package_name):
        return False
    
    @property
    def pk(self):
        return self.id


class SupabaseAuthenticationBackend(BaseBackend):
    """
    Authentication backend that uses Supabase Auth instead of Django User model
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with Supabase
        """
        if not username or not password:
            return None
        
        try:
            supabase_client = get_supabase_client()
            if not supabase_client.is_available():
                logger.warning("Supabase client not available")
                return None
            
            # Sign in with Supabase
            response = supabase_client.sign_in_user(username, password)
            
            if response and 'user' in response:
                user_data = response['user']
                
                # Check if email is verified
                if not user_data.get('email_confirmed_at'):
                    logger.warning(f"User {username} email not verified")
                    return None
                
                # Store session in request for later use
                if request:
                    request.session['supabase_session'] = response.get('session')
                
                return SupabaseUser(user_data)
            
        except Exception as e:
            logger.error(f"Supabase authentication failed for {username}: {str(e)}")
            return None
        
        return None
    
    def get_user(self, user_id):
        """
        Get user by ID from Supabase
        """
        try:
            supabase_client = get_supabase_client()
            if not supabase_client.is_available():
                return AnonymousUser()
            
            # Try to get user from current session
            user_response = supabase_client.get_user()
            if user_response and 'user' in user_response:
                user_data = user_response['user']
                if user_data.get('id') == user_id:
                    return SupabaseUser(user_data)
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
        
        return AnonymousUser()


def get_supabase_user_from_session(request):
    """
    Helper function to get current Supabase user from session
    """
    if not hasattr(request, 'session') or 'supabase_session' not in request.session:
        return AnonymousUser()
    
    try:
        supabase_client = get_supabase_client()
        if not supabase_client.is_available():
            return AnonymousUser()
        
        # Get current user
        user_response = supabase_client.get_user()
        if user_response and 'user' in user_response:
            return SupabaseUser(user_response['user'])
    
    except Exception as e:
        logger.error(f"Failed to get user from session: {str(e)}")
    
    return AnonymousUser()
