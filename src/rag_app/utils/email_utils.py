"""
Email utility functions for user verification and password reset
"""

import uuid
import logging
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from ..email_service import GoogleAppsScriptEmailService

logger = logging.getLogger(__name__)

class EmailVerificationManager:
    """
    Manages email verification tokens and sending verification emails
    """
    
    def __init__(self):
        self.email_service = GoogleAppsScriptEmailService()
        self.token_expiry_hours = 24
    
    def generate_verification_token(self, user):
        """
        Generate a unique verification token for a user
        
        Args:
            user (User): Django user instance
        
        Returns:
            str: Verification token
        """
        token = str(uuid.uuid4())
        cache_key = f"email_verification_{token}"
        
        # Store token in cache with expiry
        cache.set(cache_key, {
            'user_id': user.id,
            'email': user.email,
            'created_at': datetime.now().isoformat()
        }, timeout=self.token_expiry_hours * 3600)
        
        return token
    
    def verify_token(self, token):
        """
        Verify and consume a verification token
        
        Args:
            token (str): Verification token
        
        Returns:
            User or None: User instance if token is valid, None otherwise
        """
        cache_key = f"email_verification_{token}"
        token_data = cache.get(cache_key)
        
        if not token_data:
            return None
        
        try:
            user = User.objects.get(id=token_data['user_id'])
            # Delete the token after successful verification
            cache.delete(cache_key)
            return user
        except User.DoesNotExist:
            cache.delete(cache_key)
            return None
    
    def send_verification_email(self, user, request=None):
        """
        Send verification email to user
        
        Args:
            user (User): Django user instance
            request (HttpRequest, optional): Django request object
        
        Returns:
            dict: Result of email sending
        """
        try:
            # Generate verification token
            token = self.generate_verification_token(user)
            
            # Get user's display name
            user_name = user.get_full_name() or user.username
            
            # Send email via Google Apps Script
            result = self.email_service.send_verification_email(
                user_email=user.email,
                user_name=user_name,
                verification_token=token,
                request=request
            )
            
            if result.get('success'):
                logger.info(f"Verification email sent to {user.email}")
            else:
                logger.error(f"Failed to send verification email to {user.email}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending verification email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class PasswordResetManager:
    """
    Manages password reset tokens and sending reset emails
    """
    
    def __init__(self):
        self.email_service = GoogleAppsScriptEmailService()
        self.token_expiry_hours = 1  # Password reset tokens expire in 1 hour
    
    def generate_reset_token(self, user):
        """
        Generate a unique password reset token for a user
        
        Args:
            user (User): Django user instance
        
        Returns:
            str: Reset token
        """
        token = str(uuid.uuid4())
        cache_key = f"password_reset_{token}"
        
        # Store token in cache with expiry
        cache.set(cache_key, {
            'user_id': user.id,
            'email': user.email,
            'created_at': datetime.now().isoformat()
        }, timeout=self.token_expiry_hours * 3600)
        
        return token
    
    def verify_reset_token(self, token):
        """
        Verify a password reset token
        
        Args:
            token (str): Reset token
        
        Returns:
            User or None: User instance if token is valid, None otherwise
        """
        cache_key = f"password_reset_{token}"
        token_data = cache.get(cache_key)
        
        if not token_data:
            return None
        
        try:
            user = User.objects.get(id=token_data['user_id'])
            return user
        except User.DoesNotExist:
            cache.delete(cache_key)
            return None
    
    def consume_reset_token(self, token):
        """
        Verify and consume a password reset token
        
        Args:
            token (str): Reset token
        
        Returns:
            User or None: User instance if token is valid, None otherwise
        """
        user = self.verify_reset_token(token)
        if user:
            cache_key = f"password_reset_{token}"
            cache.delete(cache_key)
        return user
    
    def send_password_reset_email(self, user, request=None):
        """
        Send password reset email to user
        
        Args:
            user (User): Django user instance
            request (HttpRequest, optional): Django request object
        
        Returns:
            dict: Result of email sending
        """
        try:
            # Generate reset token
            token = self.generate_reset_token(user)
            
            # Get user's display name
            user_name = user.get_full_name() or user.username
            
            # Send email via Google Apps Script
            result = self.email_service.send_password_reset_email(
                user_email=user.email,
                user_name=user_name,
                reset_token=token,
                request=request
            )
            
            if result.get('success'):
                logger.info(f"Password reset email sent to {user.email}")
            else:
                logger.error(f"Failed to send password reset email to {user.email}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience functions for easy import
email_verification_manager = EmailVerificationManager()
password_reset_manager = PasswordResetManager()
