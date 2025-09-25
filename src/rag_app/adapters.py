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

User = get_user_model()


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
