"""
Authentication views for Supabase-only authentication
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.generic import FormView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from .forms_supabase import SupabaseSignUpForm, SupabaseLoginForm, SupabasePasswordResetForm
from .auth_backends import SupabaseUser, get_supabase_user_from_session
from .supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class SupabaseSignUpView(FormView):
    """Custom signup view using Supabase Auth only"""
    form_class = SupabaseSignUpForm
    template_name = 'registration/signup.html'
    
    def form_valid(self, form):
        try:
            response = form.save()
            
            if response and 'user' in response:
                messages.success(
                    self.request, 
                    'Account created successfully! Please check your email to verify your account before logging in.'
                )
                return redirect('rag_app:email_verification_sent')
            else:
                messages.error(self.request, 'Failed to create account. Please try again.')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Signup failed: {str(e)}")
            messages.error(self.request, 'Failed to create account. Please try again.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class SupabaseLoginView(FormView):
    """Custom login view using Supabase Auth only"""
    form_class = SupabaseLoginForm
    template_name = 'registration/login.html'
    
    def form_valid(self, form):
        try:
            # Get the Supabase response from the form
            response = getattr(form, 'supabase_response', None)
            
            if response and 'user' in response:
                # Create SupabaseUser object
                user = SupabaseUser(response['user'])
                
                # Store session data
                self.request.session['supabase_session'] = response.get('session')
                self.request.session['supabase_user_id'] = user.id
                self.request.session['supabase_user_email'] = user.email
                
                # Log user in (this will work with our custom backend)
                login(self.request, user, backend='rag_app.auth_backends.SupabaseAuthenticationBackend')
                
                messages.success(self.request, f'Welcome back, {user.get_short_name()}!')
                return redirect('rag_app:dashboard')
            else:
                messages.error(self.request, 'Login failed. Please try again.')
                return self.form_invalid(form)
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            messages.error(self.request, 'Login failed. Please try again.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password. Please try again.')
        return super().form_invalid(form)


class SupabaseLogoutView(View):
    """Custom logout view that also signs out from Supabase"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Sign out from Supabase
            try:
                supabase_client = get_supabase_client()
                if supabase_client.is_available():
                    supabase_client.sign_out_user()
            except Exception as e:
                logger.warning(f"Failed to sign out from Supabase: {str(e)}")
            
            # Clear Django session
            logout(request)
            messages.info(request, 'You have been logged out successfully.')
        
        return redirect('rag_app:home')


class SupabasePasswordResetView(FormView):
    """Custom password reset view using Supabase"""
    form_class = SupabasePasswordResetForm
    template_name = 'registration/password_reset.html'
    success_url = reverse_lazy('rag_app:password_reset_done')
    
    def form_valid(self, form):
        try:
            form.send_reset_email()
            messages.success(
                self.request, 
                'Password reset email has been sent. Please check your inbox.'
            )
        except Exception as e:
            logger.error(f"Password reset failed: {str(e)}")
            messages.error(self.request, 'Failed to send reset email. Please try again.')
            return self.form_invalid(form)
        
        return super().form_valid(form)


def email_verification_sent(request):
    """View to show email verification sent message"""
    return render(request, 'registration/email_verification_sent.html')


def password_reset_done(request):
    """View to show password reset email sent"""
    return render(request, 'registration/password_reset_done.html')


def resend_verification_email(request):
    """Resend email verification"""
    email = request.session.get('supabase_user_email')
    if not email:
        messages.error(request, 'No email found to send verification to.')
        return redirect('rag_app:login')
    
    try:
        supabase_client = get_supabase_client()
        if supabase_client.is_available():
            response = supabase_client.resend_verification_email(email)
            messages.success(request, 'Verification email has been resent.')
        else:
            messages.error(request, 'Email service is not available.')
    except Exception as e:
        logger.error(f"Failed to resend verification email: {str(e)}")
        messages.error(request, 'Failed to resend verification email. Please try again.')
    
    return redirect('rag_app:email_verification_sent')


def verify_email(request):
    """Handle email verification callback from Supabase"""
    token = request.GET.get('token')
    token_type = request.GET.get('type')
    
    if token and token_type == 'signup':
        try:
            supabase_client = get_supabase_client()
            if supabase_client.is_available():
                # Verify the email token
                response = supabase_client.verify_otp(token, 'signup')
                
                if response and 'user' in response:
                    messages.success(request, 'Email verified successfully! You can now log in.')
                    return redirect('rag_app:login')
                else:
                    messages.error(request, 'Invalid verification token.')
            else:
                messages.error(request, 'Email verification service is not available.')
        except Exception as e:
            logger.error(f"Email verification failed: {str(e)}")
            messages.error(request, 'Email verification failed. Please try again.')
    else:
        messages.error(request, 'Invalid verification link.')
    
    return redirect('rag_app:login')


@login_required
def profile_view(request):
    """View user profile"""
    user = get_supabase_user_from_session(request)
    return render(request, 'rag_app/profile.html', {'user': user})


def get_current_user_data(request):
    """Helper function to get current user data for templates"""
    if hasattr(request, 'user') and request.user.is_authenticated:
        if isinstance(request.user, SupabaseUser):
            return request.user
        
        # Try to get from session
        return get_supabase_user_from_session(request)
    
    return None
