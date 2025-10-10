"""
Custom Django Email Backend for Google Apps Script Integration
"""
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from .email_service import GoogleAppsScriptEmailService
import re

logger = logging.getLogger(__name__)


class GoogleAppsScriptBackend(BaseEmailBackend):
    """
    Email backend that sends emails through Google Apps Script
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        try:
            self.email_service = GoogleAppsScriptEmailService()
        except Exception as e:
            logger.error(f"Failed to initialize Google Apps Script Email Service: {e}")
            self.email_service = None
    
    def send_messages(self, email_messages):
        """
        Send multiple email messages
        """
        if not email_messages:
            return 0
        
        if not self.email_service:
            logger.error("Email service not available")
            return 0
        
        sent_count = 0
        for message in email_messages:
            if self._send_message(message):
                sent_count += 1
        
        return sent_count
    
    def _send_message(self, message):
        """
        Send a single email message through Google Apps Script
        """
        try:
            if not message.to:
                logger.error("No recipients specified")
                return False
            
            email = message.to[0]  # Get first recipient
            subject = message.subject
            body = message.body
            
            # Extract user name from message
            user_name = self._extract_user_name(body, email)
            
            # Determine email type and extract tokens
            if 'verify' in subject.lower() or 'confirm' in subject.lower():
                token = self._extract_verification_token(body)
                if token:
                    result = self.email_service.send_verification_email(
                        email, user_name, token
                    )
                    return result.get('success', False)
            
            elif 'reset' in subject.lower() or 'password' in subject.lower():
                token = self._extract_reset_token(body)
                if token:
                    result = self.email_service.send_password_reset_email(
                        email, user_name, token
                    )
                    return result.get('success', False)
            
            logger.warning(f"Unknown email type: {subject}")
            return False
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            if not self.fail_silently:
                raise
            return False
    
    def _extract_user_name(self, body, email):
        """Extract user name from email body or use email prefix"""
        # Look for patterns like "Hello Name" or "Hi Name"
        patterns = [
            r'(?:Hello|Hi|Dear)\s+([^\s,!.\n]+)',
            r'user[_\s]*name["\']?\s*:\s*["\']?([^"\',\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if name and name.lower() not in ['user', 'there', 'customer']:
                    return name
        
        # Fallback to email prefix
        return email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
    
    def _extract_verification_token(self, body):
        """Extract verification token from email body"""
        patterns = [
            r'/verify[^/]*?/([a-zA-Z0-9\-_]+)/',
            r'/accounts/confirm-email/([a-zA-Z0-9\-_]+)/',
            r'confirmation[_\s]*key["\']?\s*:\s*["\']?([a-zA-Z0-9\-_]+)',
            r'token=([a-zA-Z0-9\-_]+)',
            r'key=([a-zA-Z0-9\-_]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_reset_token(self, body):
        """Extract password reset token from email body"""
        patterns = [
            r'/password[^/]*?reset[^/]*?/([a-zA-Z0-9\-_]+)/([a-zA-Z0-9\-_]+)/',
            r'/reset[^/]*?/([a-zA-Z0-9\-_]+)/([a-zA-Z0-9\-_]+)/',
            r'reset[_\s]*token["\']?\s*:\s*["\']?([a-zA-Z0-9\-_]+)',
            r'uid=([a-zA-Z0-9\-_]+).*?token=([a-zA-Z0-9\-_]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    return f"{groups[0]}-{groups[1]}"
                else:
                    return groups[0]
        
        return None
