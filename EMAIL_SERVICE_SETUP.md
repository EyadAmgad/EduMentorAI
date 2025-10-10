# 🚀 EduMentorAI Email Service Setup Guide

## Overview

This guide helps you set up the Google Apps Script email service for EduMentorAI, replacing Django's built-in email system. Perfect for Hugging Face deployments where SMTP is restricted.

## 📋 What's Included

- ✅ **Google Apps Script email service** with beautiful HTML templates
- ✅ **Django integration** with email verification and password reset
- ✅ **Simple password authentication** (no complex API keys)
- ✅ **Professional email templates** matching your brand
- ✅ **Token-based verification system**
- ✅ **Optional Google Sheets logging**

## 🔧 Part 1: Google Apps Script Setup

### Step 1: Create Google Apps Script Project

1. Go to https://script.google.com/
2. Click "**New project**"
3. Delete the default code
4. Copy and paste the code from `google_apps_script/email_service.js`
5. Save the project as "**EduMentorAI-EmailService**"

### Step 2: Configure the Script

Update the CONFIG section at the top of the script:

```javascript
const CONFIG = {
  SENDER_EMAIL: 'your-actual-gmail@gmail.com',     // Your Gmail address
  SENDER_NAME: 'EduMentorAI Support',
  DJANGO_BASE_URL: 'https://your-app-name.hf.space', // Your Hugging Face URL
  PASSWORD: 'YourSimplePassword123',               // Choose a simple password
  SPREADSHEET_ID: ''                              // Optional: leave empty for now
};
```

### Step 3: Set Up Gmail Permissions

1. In Google Apps Script, the first time you run the script, it will ask for Gmail permissions
2. Click "**Review permissions**"
3. Choose your Gmail account
4. Click "**Allow**"

### Step 4: Deploy as Web App

1. Click "**Deploy**" > "**New deployment**"
2. Click the gear icon ⚙️ next to "Type"
3. Select "**Web app**"
4. Set "**Execute as**" to "**Me**"
5. Set "**Who has access**" to "**Anyone**"
6. Click "**Deploy**"
7. **Copy the Web app URL** - you'll need this for Django!

### Step 5: Test the Script

1. In the script editor, select `testEmailSending` from the function dropdown
2. Click "**Run**"
3. Check your email for a test message
4. Check the execution log for any errors

## 🔧 Part 2: Django Integration

### Step 1: Update Django Settings

Add these settings to your `src/rag_django/settings.py`:

```python
# Google Apps Script Email Service Configuration
GOOGLE_APPS_SCRIPT_URL = 'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec'
GOOGLE_APPS_SCRIPT_PASSWORD = 'YourSimplePassword123'  # Same password as in Google Apps Script

# Email verification settings
EMAIL_VERIFICATION_REQUIRED = True

# Cache configuration (required for token storage)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 86400,  # 24 hours
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'rag_app.email_service': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Step 2: Update URLs

Add these URL patterns to your `src/rag_app/urls.py`:

```python
from django.urls import path
from .views.email_views import (
    verify_email_view,
    resend_verification_email_view,
    email_verification_required_view,
    password_reset_request_view,
    password_reset_confirm_view,
    password_reset_done_view,
)

# Add to your existing urlpatterns:
urlpatterns = [
    # ... your existing patterns ...
    
    # Email verification URLs
    path('verify-email/<str:token>/', verify_email_view, name='verify_email'),
    path('resend-verification/', resend_verification_email_view, name='resend_verification'),
    path('email-verification-required/', email_verification_required_view, name='email_verification_required'),
    
    # Password reset URLs
    path('password-reset/', password_reset_request_view, name='password_reset'),
    path('reset-password/<str:token>/', password_reset_confirm_view, name='password_reset_confirm'),
    path('password-reset/done/', password_reset_done_view, name='password_reset_done'),
]
```

### Step 3: Update User Registration

In your existing signup view, integrate email verification:

```python
from rag_app.utils.email_utils import email_verification_manager

def signup_view(request):
    if request.method == 'POST':
        form = YourSignupForm(request.POST)
        
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until email is verified
            user.save()
            
            # Send verification email
            result = email_verification_manager.send_verification_email(user, request)
            
            if result.get('success'):
                messages.success(request, 
                    "✅ Account created! Please check your email to verify your account.")
                return redirect('email_verification_required')
            else:
                messages.error(request, 
                    "⚠️ Account created but failed to send verification email.")
                
    return render(request, 'registration/signup.html', {'form': form})
```

### Step 4: Add Required Dependencies

Add to your `requirements.txt`:

```
requests>=2.25.0
```

## 🧪 Testing

### Test Google Apps Script

1. Run the `testEmailSending()` function in Google Apps Script
2. Check your email for the test message
3. Verify no errors in execution logs

### Test Django Integration

1. Try registering a new user
2. Check if verification email is received
3. Click the verification link
4. Test password reset functionality
5. Verify both light and dark mode work in emails

## 🔒 Security Features

- **Simple password authentication** between Django and Google Apps Script
- **Single-use tokens** that expire automatically
- **IP address logging** for security monitoring
- **Secure token storage** using Django's cache system
- **No sensitive data in URLs**

## 📊 Optional: Google Sheets Logging

### Enable Logging (Optional)

1. Create a new Google Sheet
2. Copy the Sheet ID from the URL (between `/d/` and `/edit`)
3. Add the Sheet ID to your Google Apps Script CONFIG
4. The script will automatically log all email requests

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid password" error**
   - Ensure passwords match exactly in both Django and Google Apps Script
   - Check for extra spaces

2. **Gmail permissions denied**
   - Re-run the script and grant permissions
   - Make sure you're using the correct Gmail account

3. **Email not received**
   - Check spam folder
   - Verify Gmail account can send emails
   - Check Google Apps Script execution logs

4. **URL not found (404)**
   - Make sure you copied the correct Web app URL
   - Verify the URL ends with `/exec`

### Debug Steps

1. Check Google Apps Script logs: **View** > **Logs**
2. Test with the `testEmailSending()` function
3. Check Django logs for HTTP errors
4. Verify all configuration values

## 🌟 Email Features

- **Beautiful HTML emails** with your brand colors
- **Mobile-responsive** design
- **Professional templates** for verification and password reset
- **Fallback text versions** for compatibility
- **Emoji icons** for visual appeal
- **Security warnings** and expiration notices

## 💡 Benefits

✅ **Free** - Uses Gmail's free tier
✅ **Reliable** - Google's infrastructure
✅ **No SMTP issues** - Perfect for Hugging Face
✅ **Professional** - Beautiful email templates
✅ **Secure** - Password authentication + token system
✅ **Easy setup** - No complex configuration
✅ **Scalable** - Handles reasonable email volumes

## 🎯 Quick Checklist

### Google Apps Script:
- [ ] Create new Google Apps Script project
- [ ] Copy email service code
- [ ] Update CONFIG with your details
- [ ] Grant Gmail permissions
- [ ] Deploy as web app
- [ ] Copy web app URL
- [ ] Test with `testEmailSending()`

### Django:
- [ ] Files are already created in this repository
- [ ] Update `settings.py` with your configuration
- [ ] Update `urls.py` with email URL patterns
- [ ] Update signup view for email verification
- [ ] Add `requests` to requirements.txt
- [ ] Test user registration and verification

## 🚀 Ready to Deploy!

Once everything is set up, your EduMentorAI app will have professional email verification that works perfectly on Hugging Face! Users will receive beautiful, branded emails for account verification and password resets.

---

**Need help?** Check the troubleshooting section above or review the execution logs in Google Apps Script.
