# Gmail SMTP Setup Instructions

Follow these steps to set up real email sending with Gmail SMTP for EduMentorAI:

## Prerequisites
- A Gmail account
- 2-factor authentication enabled on your Gmail account

## Steps to Set Up Gmail SMTP

### 1. Enable 2-Factor Authentication
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Click on "Security" in the left sidebar
3. Under "Signing in to Google", click on "2-Step Verification"
4. Follow the prompts to enable 2-factor authentication

### 2. Generate an App Password
1. After enabling 2-factor authentication, go back to the Security section
2. Under "Signing in to Google", click on "App passwords"
3. Select "Mail" as the app and your device type
4. Click "Generate"
5. Copy the 16-character password (it will look like: `abcd efgh ijkl mnop`)

### 3. Update Your .env File
Open your `.env` file in the `src/` directory and update these values:

```env
# Replace with your actual Gmail address
EMAIL_HOST_USER=your-email@gmail.com

# Replace with the app password you generated (remove spaces)
EMAIL_HOST_PASSWORD=abcdefghijklmnop

# Update the default from email (optional)
DEFAULT_FROM_EMAIL=EduMentorAI <your-email@gmail.com>
SERVER_EMAIL=EduMentorAI <your-email@gmail.com>
```

### 4. Test Email Sending
1. Save your `.env` file
2. Restart your Django server: `python manage.py runserver`
3. Try signing up with a new account
4. Check if you receive the verification email in your inbox

## Alternative: Using Other Email Providers

### Outlook/Hotmail
```env
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-password
```

### Yahoo Mail
```env
EMAIL_HOST=smtp.mail.yahoo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yahoo.com
EMAIL_HOST_PASSWORD=your-app-password
```

## Development vs Production

### Development (Current Setup)
- If `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are empty, emails are printed to the console
- This is useful for testing without sending real emails

### Production
- Set proper SMTP credentials to send real emails
- Consider using services like SendGrid, Mailgun, or AWS SES for production

## Troubleshooting

### Common Issues:
1. **"Authentication failed"** - Check your app password is correct and doesn't contain spaces
2. **"SMTP connection failed"** - Verify your internet connection and Gmail settings
3. **Emails going to spam** - This is normal for new senders; ask users to check spam folders

### Testing Commands:
```bash
# Test email configuration in Django shell
python manage.py shell

# In the shell:
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test message body.',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Security Notes
- Never commit your actual email credentials to version control
- Use environment variables for all sensitive information
- Consider using OAuth2 for production applications
- Regularly rotate your app passwords

## Support
If you encounter issues, check:
1. Django documentation for email configuration
2. Gmail's SMTP documentation
3. Your email provider's SMTP settings
