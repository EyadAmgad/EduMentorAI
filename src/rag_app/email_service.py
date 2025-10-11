"""
Email service integration with Google Apps Script
Replaces Django's built-in email backend for Hugging Face deployment
"""

import json
import requests
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

class GoogleAppsScriptEmailService:
    """
    Email service that uses Google Apps Script as the backend
    Perfect for Hugging Face deployments where SMTP is not available
    """
    
    def __init__(self):
        # Get configuration from Django settings
        self.gas_url = getattr(settings, 'GOOGLE_APPS_SCRIPT_URL', None)
        self.api_password = getattr(settings, 'GOOGLE_APPS_SCRIPT_PASSWORD', None)
        
        if not self.gas_url or not self.api_password:
            raise ImproperlyConfigured(
                "GOOGLE_APPS_SCRIPT_URL and GOOGLE_APPS_SCRIPT_PASSWORD must be set in settings.py"
            )
    
    def send_verification_email(self, user_email, user_name, verification_token, request=None):
        """
        Send email verification email via Google Apps Script
        
        Args:
            user_email (str): Recipient email address
            user_name (str): User's display name
            verification_token (str): Unique verification token
            request (HttpRequest, optional): Django request object for IP logging
        
        Returns:
            dict: Response from the email service
        """
        payload = {
            'password': self.api_password,
            'email_type': 'verification',
            'email': user_email,
            'user_name': user_name,
            'verification_token': verification_token,
            'ip_address': self._get_client_ip(request) if request else None
        }
        
        return self._send_request(payload)
    
    def send_password_reset_email(self, user_email, user_name, reset_token, request=None):
        """
        Send password reset email via Google Apps Script
        
        Args:
            user_email (str): Recipient email address
            user_name (str): User's display name
            reset_token (str): Unique password reset token
            request (HttpRequest, optional): Django request object for IP logging
        
        Returns:
            dict: Response from the email service
        """
        payload = {
            'password': self.api_password,
            'email_type': 'password_reset',
            'email': user_email,
            'user_name': user_name,
            'reset_token': reset_token,
            'ip_address': self._get_client_ip(request) if request else None
        }
        
        return self._send_request(payload)
    
    def _send_request(self, payload):
        """
        Send HTTP request to Google Apps Script
        
        Args:
            payload (dict): Request payload
        
        Returns:
            dict: Response from the service
        """
        try:
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'EduMentorAI-Django/1.0'
            }
            
            response = requests.post(
                self.gas_url,
                json=payload,
                headers=headers,
                timeout=30  # 30 second timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                logger.info(f"Email sent successfully to {payload.get('email')}")
            else:
                logger.error(f"Email sending failed: {result.get('error')}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}'
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid response format'
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _get_client_ip(self, request):
        """
        Get client IP address from request
        
        Args:
            request (HttpRequest): Django request object
        
        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
