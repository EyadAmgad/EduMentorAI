/**
 * EduMentorAI Email Verification Service
 * Google Apps Script to handle email verification for Django app
 * Author: Assistant for EduMentorAI
 * Date: October 10, 2025
 */

// Configuration - Update these values
const CONFIG = {
  SENDER_EMAIL: 'edumentorai25@gmail.com', // Your Gmail address
  SENDER_NAME: 'EduMentorAI Support',
  DJANGO_BASE_URL: 'http://localhost:8000', // Your local development URL
  PASSWORD: 'V@g@bond0603', // Simple password for authentication
  SPREADSHEET_ID: '' // Optional: for logging
};

/**
 * Main function to handle POST requests for sending emails
 */
function doPost(e) {
  try {
    // Parse the request data
    const data = JSON.parse(e.postData.contents);
    
    // Validate password
    if (data.password !== CONFIG.PASSWORD) {
      return ContentService
        .createTextOutput(JSON.stringify({
          success: false,
          error: 'Invalid password'
        }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    let result;
    
    // Handle different email types
    switch (data.email_type) {
      case 'verification':
        if (!data.email || !data.verification_token || !data.user_name) {
          throw new Error('Missing required fields for verification email');
        }
        result = sendVerificationEmail(data);
        break;
        
      case 'password_reset':
        if (!data.email || !data.reset_token || !data.user_name) {
          throw new Error('Missing required fields for password reset email');
        }
        result = sendPasswordResetEmail(data);
        break;
        
      default:
        throw new Error('Invalid email_type. Must be "verification" or "password_reset"');
    }
    
    // Log the request
    logEmailRequest(data, result);
    
    return ContentService
      .createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch (error) {
    console.error('Error in doPost:', error);
    return ContentService
      .createTextOutput(JSON.stringify({
        success: false,
        error: error.toString()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Send verification email using Gmail API
 */
function sendVerificationEmail(data) {
  try {
    const verificationUrl = `${CONFIG.DJANGO_BASE_URL}/accounts/confirm-email/${data.verification_token}/`;
    
    const subject = 'Verify Your EduMentorAI Account';
    
    const htmlBody = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }
        .header p {
            margin: 10px 0 0;
            opacity: 0.9;
            font-size: 16px;
        }
        .content {
            padding: 40px 30px;
        }
        .greeting {
            font-size: 18px;
            margin-bottom: 20px;
            color: #1f2937;
        }
        .message {
            font-size: 16px;
            margin-bottom: 30px;
            color: #4b5563;
            line-height: 1.7;
        }
        .verify-btn {
            display: inline-block;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white !important;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            text-align: center;
            transition: transform 0.2s ease;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        .verify-btn:hover {
            transform: translateY(-2px);
        }
        .alternative {
            margin-top: 30px;
            padding: 20px;
            background: #f3f4f6;
            border-radius: 8px;
            font-size: 14px;
            color: #6b7280;
        }
        .alternative a {
            color: #10b981;
            word-break: break-all;
        }
        .footer {
            text-align: center;
            padding: 30px;
            font-size: 14px;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
        }
        .footer a {
            color: #10b981;
            text-decoration: none;
        }
        .security-note {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
            color: #92400e;
        }
        .security-note strong {
            color: #78350f;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎓 EduMentorAI</h1>
            <p>Your AI-Powered Learning Companion</p>
        </div>
        
        <div class="content">
            <div class="greeting">Hello ${data.user_name}! 👋</div>
            
            <div class="message">
                Welcome to EduMentorAI! We're excited to have you join our learning community. 
                To get started and ensure the security of your account, please verify your email address by clicking the button below.
            </div>
            
            <div style="text-align: center;">
                <a href="${verificationUrl}" class="verify-btn">
                    ✅ Verify My Email Address
                </a>
            </div>
            
            <div class="alternative">
                <strong>Can't click the button?</strong> Copy and paste this link into your browser:<br>
                <a href="${verificationUrl}">${verificationUrl}</a>
            </div>
            
            <div class="security-note">
                <strong>🔒 Security Note:</strong> This verification link will expire in 24 hours for your security. 
                If you didn't create an account with EduMentorAI, please ignore this email.
            </div>
        </div>
        
        <div class="footer">
            <p>
                Need help? Contact us at 
                <a href="mailto:support@edumentorai.com">support@edumentorai.com</a>
            </p>
            <p>
                © 2025 EduMentorAI. All rights reserved.<br>
                <a href="${CONFIG.DJANGO_BASE_URL}">Visit EduMentorAI</a>
            </p>
        </div>
    </div>
</body>
</html>
    `;
    
    const textBody = `
Hello ${data.user_name}!

Welcome to EduMentorAI! We're excited to have you join our learning community.

To verify your email address and activate your account, please click the following link:
${verificationUrl}

This verification link will expire in 24 hours for security purposes.

If you didn't create an account with EduMentorAI, please ignore this email.

Need help? Contact us at support@edumentorai.com

Best regards,
The EduMentorAI Team

© 2025 EduMentorAI. All rights reserved.
Visit us at: ${CONFIG.DJANGO_BASE_URL}
    `;
    
    // Send the email
    GmailApp.sendEmail(
      data.email,
      subject,
      textBody,
      {
        htmlBody: htmlBody,
        name: CONFIG.SENDER_NAME,
        from: CONFIG.SENDER_EMAIL
      }
    );
    
    return {
      success: true,
      message: 'Verification email sent successfully',
      timestamp: new Date().toISOString()
    };
    
  } catch (error) {
    console.error('Error sending email:', error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Function to handle password reset emails
 */
function sendPasswordResetEmail(data) {
  try {
    const resetUrl = `${CONFIG.DJANGO_BASE_URL}/accounts/password/reset/key/${data.reset_token}/`;
    
    const subject = 'Reset Your EduMentorAI Password';
    
    const htmlBody = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9fafb;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 28px;
            font-weight: 700;
        }
        .content {
            padding: 40px 30px;
        }
        .message {
            font-size: 16px;
            margin-bottom: 30px;
            color: #4b5563;
            line-height: 1.7;
        }
        .reset-btn {
            display: inline-block;
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white !important;
            text-decoration: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 16px;
            text-align: center;
            transition: transform 0.2s ease;
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
        }
        .reset-btn:hover {
            transform: translateY(-2px);
        }
        .security-note {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
            color: #991b1b;
        }
        .footer {
            text-align: center;
            padding: 30px;
            font-size: 14px;
            color: #9ca3af;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Password Reset</h1>
        </div>
        
        <div class="content">
            <div class="message">
                Hello ${data.user_name},<br><br>
                We received a request to reset the password for your EduMentorAI account. 
                If you made this request, click the button below to reset your password.
            </div>
            
            <div style="text-align: center;">
                <a href="${resetUrl}" class="reset-btn">
                    🔄 Reset My Password
                </a>
            </div>
            
            <div class="security-note">
                <strong>🔒 Security Note:</strong> This password reset link will expire in 1 hour. 
                If you didn't request a password reset, please ignore this email and your password will remain unchanged.
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 EduMentorAI. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
    `;
    
    // Send the email
    GmailApp.sendEmail(
      data.email,
      subject,
      `Hello ${data.user_name}, Click this link to reset your password: ${resetUrl}`,
      {
        htmlBody: htmlBody,
        name: CONFIG.SENDER_NAME,
        from: CONFIG.SENDER_EMAIL
      }
    );
    
    return {
      success: true,
      message: 'Password reset email sent successfully',
      timestamp: new Date().toISOString()
    };
    
  } catch (error) {
    console.error('Error sending password reset email:', error);
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Optional: Log email requests to a Google Sheet
 */
function logEmailRequest(data, result) {
  try {
    if (!CONFIG.SPREADSHEET_ID) return;
    
    const sheet = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID).getActiveSheet();
    
    // Add headers if sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, 6).setValues([[
        'Timestamp', 'Email', 'User Name', 'Success', 'Error', 'IP Address'
      ]]);
    }
    
    // Add the log entry
    sheet.appendRow([
      new Date(),
      data.email,
      data.user_name,
      result.success,
      result.error || '',
      data.ip_address || 'N/A'
    ]);
    
  } catch (error) {
    console.error('Error logging to sheet:', error);
  }
}

/**
 * Test function - you can run this to test the email functionality
 */
function testEmailSending() {
  const testData = {
    password: CONFIG.PASSWORD,
    email_type: 'verification',
    email: 'test@example.com',
    user_name: 'Test User',
    verification_token: 'test-token-123',
    ip_address: '127.0.0.1'
  };
  
  const result = sendVerificationEmail(testData);
  console.log('Test result:', result);
  return result;
}
