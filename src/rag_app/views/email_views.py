"""
Views for handling email verification and password reset
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.db import transaction
import logging

from ..utils.email_utils import email_verification_manager, password_reset_manager

logger = logging.getLogger(__name__)


def verify_email_view(request, token):
    """
    Handle email verification via token
    
    Args:
        request (HttpRequest): Django request
        token (str): Verification token from URL
    
    Returns:
        HttpResponse: Rendered template or redirect
    """
    try:
        # Verify the token and get the user
        user = email_verification_manager.verify_token(token)
        
        if user:
            # Mark email as verified
            user.is_active = True
            user.save()
            
            # Log the user in automatically after verification
            login(request, user)
            
            messages.success(
                request, 
                f"🎉 Welcome to EduMentorAI, {user.get_full_name() or user.username}! "
                "Your email has been verified successfully."
            )
            
            logger.info(f"Email verified successfully for user: {user.email}")
            
            # Redirect to dashboard or home page
            return redirect('rag_app:dashboard')
            
        else:
            messages.error(
                request,
                "❌ This verification link is invalid or has expired. "
                "Please request a new verification email."
            )
            logger.warning(f"Invalid or expired verification token: {token}")
            
            return redirect('account_login')
            
    except Exception as e:
        logger.error(f"Error during email verification: {str(e)}")
        messages.error(
            request,
            "⚠️ An error occurred during verification. Please try again or contact support."
        )
        return redirect('account_login')


def resend_verification_email_view(request):
    """
    Resend verification email to the current user
    """
    if not request.user.is_authenticated:
        messages.error(request, "Please log in to resend verification email.")
        return redirect('account_login')
    
    if request.user.is_active:
        messages.info(request, "Your email is already verified!")
        return redirect('rag_app:dashboard')
    
    try:
        result = email_verification_manager.send_verification_email(
            user=request.user,
            request=request
        )
        
        if result.get('success'):
            messages.success(
                request,
                "📧 Verification email sent! Please check your inbox and spam folder."
            )
        else:
            messages.error(
                request,
                f"Failed to send verification email: {result.get('error', 'Unknown error')}"
            )
            
    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}")
        messages.error(
            request,
            "An error occurred while sending the email. Please try again later."
        )
    
    return redirect('email_verification_required')


def email_verification_required_view(request):
    """
    Show page informing user that email verification is required
    """
    if request.user.is_authenticated and request.user.is_active:
        return redirect('rag_app:dashboard')
    
    return render(request, 'rag_app/email_verification_required.html', {
        'user_email': request.user.email if request.user.is_authenticated else None
    })


def password_reset_request_view(request):
    """
    Handle password reset request
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, 'registration/password_reset_form.html')
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            result = password_reset_manager.send_password_reset_email(
                user=user,
                request=request
            )
            
            if result.get('success'):
                messages.success(
                    request,
                    "📧 Password reset email sent! Please check your inbox and spam folder. "
                    "The link will expire in 1 hour."
                )
                return redirect('password_reset_done')
            else:
                messages.error(
                    request,
                    f"Failed to send password reset email. Please try again later."
                )
                logger.error(f"Password reset email failed: {result.get('error')}")
                
        except User.DoesNotExist:
            # Don't reveal whether the email exists or not for security
            messages.success(
                request,
                "📧 If an account with that email exists, a password reset link has been sent."
            )
            return redirect('password_reset_done')
        
        except Exception as e:
            logger.error(f"Error in password reset request: {str(e)}")
            messages.error(
                request,
                "An error occurred while processing your request. Please try again later."
            )
    
    return render(request, 'registration/password_reset_form.html')


def password_reset_confirm_view(request, token):
    """
    Handle password reset confirmation with token
    
    Args:
        request (HttpRequest): Django request
        token (str): Password reset token from URL
    """
    user = password_reset_manager.verify_reset_token(token)
    
    if not user:
        messages.error(
            request,
            "❌ This password reset link is invalid or has expired. "
            "Please request a new password reset."
        )
        return redirect('password_reset')
    
    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        
        if form.is_valid():
            try:
                # Consume the token (delete it)
                consumed_user = password_reset_manager.consume_reset_token(token)
                
                if consumed_user:
                    # Save the new password
                    form.save()
                    
                    messages.success(
                        request,
                        "🔒 Your password has been reset successfully! You can now log in with your new password."
                    )
                    
                    logger.info(f"Password reset completed for user: {user.email}")
                    return redirect('account_login')
                else:
                    messages.error(
                        request,
                        "❌ This password reset link has already been used or has expired."
                    )
                    return redirect('password_reset')
                    
            except Exception as e:
                logger.error(f"Error completing password reset: {str(e)}")
                messages.error(
                    request,
                    "An error occurred while resetting your password. Please try again."
                )
        
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'registration/password_reset_confirm.html', {
        'form': form,
        'user': user,
        'token': token
    })


def password_reset_done_view(request):
    """
    Show confirmation that password reset email was sent
    """
    return render(request, 'registration/password_reset_done.html')


@require_http_methods(["POST"])
@csrf_exempt
def webhook_email_status(request):
    """
    Optional webhook endpoint to receive email delivery status from Google Apps Script
    """
    try:
        import json
        data = json.loads(request.body)
        
        # Log email delivery status
        logger.info(f"Email webhook received: {data}")
        
        return JsonResponse({'status': 'received'})
        
    except Exception as e:
        logger.error(f"Error processing email webhook: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
