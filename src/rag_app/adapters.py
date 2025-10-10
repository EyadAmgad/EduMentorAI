"""
Custom AllAuth adapters for EduMentorAI
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django import forms
from .email_service import GoogleAppsScriptEmailService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to handle signup behavior for existing users"""
    
    def clean_email(self, email):
        """
        Override to add custom email validation during signup
        """
        # First run the default validation
        email = super().clean_email(email)
        
        # Check if user already exists during signup
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email address already exists. "
                "Please sign in instead or use the 'Forgot Password' option if you can't remember your password."
            )
        
        return email
    
    def save_user(self, request, user, form, commit=True):
        """
        Override to handle existing user signup attempts
        """
        # The clean_email method should have already caught duplicate emails
        # But as a fallback, check again
        email = form.cleaned_data.get('email')
        
        if User.objects.filter(email=email).exists():
            # Add error message and return None to prevent user creation
            messages.error(
                request, 
                f"An account with email '{email}' already exists. "
                "Please sign in instead or use the 'Forgot Password' option if you can't remember your password."
            )
            return None
            
        # If no existing user, proceed with normal user creation
        return super().save_user(request, user, form, commit)
    
    def respond_user_inactive(self, request, user):
        """Handle inactive user response"""
        messages.error(
            request,
            "Your account is inactive. Please contact support for assistance."
        )
        return redirect('account_login')
    
    def get_login_redirect_url(self, request):
        """Redirect after successful login"""
        return '/dashboard/'
    
    def get_logout_redirect_url(self, request):
        """Redirect after logout"""
        return '/'
    
    def get_signup_redirect_url(self, request):
        """Redirect after successful signup"""
        return '/dashboard/'
    
    def send_account_already_exists_mail(self, email):
        """
        Override to prevent sending account already exists email
        This prevents the automatic password reset flow and connection errors
        """
        # Do nothing - we handle this in clean_email instead with a proper error message
        pass

    def send_mail(self, template_prefix, email, context):
        """
        Override to use Google Apps Script for email sending
        This replaces Django's default email backend
        """
        try:
            email_service = GoogleAppsScriptEmailService()
            user = context.get('user')
            request = context.get('request')
            
            if not user:
                logger.error("No user found in email context")
                return
            
            # Build user name from available data
            user_name = ''
            if hasattr(user, 'first_name') and user.first_name:
                user_name = user.first_name
                if hasattr(user, 'last_name') and user.last_name:
                    user_name += f" {user.last_name}"
            elif hasattr(user, 'username') and user.username:
                user_name = user.username
            else:
                user_name = email.split('@')[0]
            
            logger.info(f"Sending email with template: {template_prefix}")
            logger.info(f"Context keys: {list(context.keys())}")
            
            # Handle email verification
            if 'email_confirmation' in template_prefix:
                # Try multiple ways to get the verification key
                verification_token = None
                
                # Method 1: email_address object
                email_address = context.get('email_address')
                if email_address and hasattr(email_address, 'key'):
                    verification_token = email_address.key
                    logger.info(f"Found verification token from email_address: {verification_token}")
                
                # Method 2: direct key in context
                if not verification_token:
                    verification_token = context.get('key')
                    if verification_token:
                        logger.info(f"Found verification token from context key: {verification_token}")
                
                # Method 3: confirmation key
                if not verification_token:
                    verification_token = context.get('confirmation_key')
                    if verification_token:
                        logger.info(f"Found verification token from confirmation_key: {verification_token}")
                
                # Method 4: extract from activate_url
                if not verification_token:
                    activate_url = context.get('activate_url', '')
                    if activate_url:
                        import re
                        match = re.search(r'/([a-zA-Z0-9\-_]+)/?$', activate_url)
                        if match:
                            verification_token = match.group(1)
                            logger.info(f"Found verification token from URL: {verification_token}")
                
                if verification_token:
                    result = email_service.send_verification_email(
                        email, user_name, verification_token, request
                    )
                    if result.get('success'):
                        logger.info(f"Verification email sent successfully to {email}")
                    else:
                        logger.error(f"Failed to send verification email: {result.get('error')}")
                else:
                    logger.error("No verification key found in email context")
                    logger.error(f"Available context: {context}")
            
            # Handle password reset
            elif 'password_reset' in template_prefix:
                # Extract reset token from context
                uid = context.get('uid')
                token = context.get('token')
                if uid and token:
                    reset_token = f"{uid}-{token}"
                    result = email_service.send_password_reset_email(
                        email, user_name, reset_token, request
                    )
                    if result.get('success'):
                        logger.info(f"Password reset email sent successfully to {email}")
                    else:
                        logger.error(f"Failed to send password reset email: {result.get('error')}")
                else:
                    logger.error("No reset token found in email context")
                    logger.error(f"Available context: {context}")
            
            else:
                logger.warning(f"Unknown email template: {template_prefix}")
                
        except Exception as e:
            logger.error(f"Error in send_mail: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Don't raise the exception to prevent breaking the flow
            pass
