from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from allauth.account.models import EmailAddress


class EmailVerificationMiddleware:
    """
    Middleware to enforce email verification before allowing access to the site
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that don't require email verification
        self.exempt_urls = [
            '/accounts/',  # AllAuth URLs
            '/admin/',     # Admin URLs
            '/static/',    # Static files
            '/media/',     # Media files
        ]
    
    def __call__(self, request):
        # Check if user is authenticated and if email verification is required
        if (request.user.is_authenticated and 
            not request.user.is_superuser and 
            not self.is_exempt_url(request.path)):
            
            # Check if user has verified email
            if not self.user_has_verified_email(request.user):
                # Redirect to email verification page
                return redirect(reverse('account_email_verification_sent'))
        
        response = self.get_response(request)
        return response
    
    def is_exempt_url(self, path):
        """Check if the URL is exempt from email verification"""
        return any(path.startswith(exempt) for exempt in self.exempt_urls)
    
    def user_has_verified_email(self, user):
        """Check if user has at least one verified email"""
        try:
            return EmailAddress.objects.filter(
                user=user, 
                verified=True
            ).exists()
        except:
            return False
