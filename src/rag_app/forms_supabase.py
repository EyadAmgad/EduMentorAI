"""
Django forms for EduMentorAI - Supabase Auth Only
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Subject, Document, Quiz, UserProfile, ChatMessage
from .supabase_client import get_supabase_client
import logging

logger = logging.getLogger(__name__)


class SupabaseSignUpForm(forms.Form):
    """Custom signup form that works with Supabase Auth only"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name',
            'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name',
            'autocomplete': 'family-name'
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })
    )
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match.")
        
        return password2
    
    def save(self):
        """Create user in Supabase Auth"""
        try:
            supabase_client = get_supabase_client()
            if not supabase_client.is_available():
                raise ValidationError("Authentication service is not available.")
            
            response = supabase_client.create_user(
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password1'],
                email_confirm=True,  # This triggers email verification
                data={
                    'first_name': self.cleaned_data.get('first_name', ''),
                    'last_name': self.cleaned_data.get('last_name', ''),
                }
            )
            
            logger.info(f"User created in Supabase: {self.cleaned_data['email']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create user in Supabase: {str(e)}")
            raise ValidationError(f"Failed to create account: {str(e)}")


class SupabaseLoginForm(forms.Form):
    """Custom login form that works with Supabase Auth only"""
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            try:
                supabase_client = get_supabase_client()
                if not supabase_client.is_available():
                    raise ValidationError("Authentication service is not available.")
                
                response = supabase_client.sign_in_user(email, password)
                
                if not response or 'user' not in response:
                    raise ValidationError("Invalid email or password.")
                
                user_data = response['user']
                
                # Check if email is verified
                if not user_data.get('email_confirmed_at'):
                    raise ValidationError(
                        "Please verify your email address before logging in. "
                        "Check your inbox for a verification link."
                    )
                
                # Store the response for later use
                self.supabase_response = response
                
            except ValidationError:
                raise
            except Exception as e:
                logger.error(f"Supabase authentication failed: {str(e)}")
                raise ValidationError("Authentication failed. Please try again.")
        
        return self.cleaned_data


class SupabasePasswordResetForm(forms.Form):
    """Custom password reset form that works with Supabase"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    
    def send_reset_email(self):
        """Send password reset email via Supabase"""
        email = self.cleaned_data.get('email')
        try:
            supabase_client = get_supabase_client()
            if supabase_client.is_available():
                response = supabase_client.reset_password_email(email)
                return response
        except Exception as e:
            logger.error(f"Failed to send reset email via Supabase: {str(e)}")
            raise ValidationError("Failed to send reset email. Please try again.")


# Keep existing forms for Django models
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class SubjectForm(forms.ModelForm):
    """Form for creating/editing subjects"""
    
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter subject name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., CS101'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter subject description (optional)'
            })
        }


class DocumentUploadForm(forms.ModelForm):
    """Form for uploading documents"""
    
    files = MultipleFileField(
        required=True,
        help_text='Select one or more files (PDF, DOC, DOCX, TXT, PPT, PPTX)'
    )
    
    class Meta:
        model = Document
        fields = ['title', 'subject', 'files']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter document title (optional - will use filename if empty)'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filter subjects for the current user only
            self.fields['subject'].queryset = Subject.objects.filter(created_by=user)
        
        # Make title optional since we can generate it from filename
        self.fields['title'].required = False


class QuizCreateForm(forms.ModelForm):
    """Form for creating quizzes"""
    
    class Meta:
        model = Quiz
        fields = ['title', 'subject', 'based_on_document', 'description', 
                 'time_limit', 'total_questions']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter quiz title'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-control'
            }),
            'based_on_document': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter quiz description (optional)'
            }),
            'time_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 180,
                'placeholder': 'Time limit in minutes'
            }),
            'total_questions': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50,
                'placeholder': 'Number of questions'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(created_by=user)
            self.fields['based_on_document'].queryset = Document.objects.filter(
                uploaded_by=user, processed=True
            )
        
        # Make based_on_document optional
        self.fields['based_on_document'].required = False
        self.fields['based_on_document'].empty_label = "Generate from all subject documents"


class ChatMessageForm(forms.ModelForm):
    """Form for chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Type your message here...',
                'style': 'resize: none;'
            })
        }


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile - works with Supabase user data"""
    
    # Fields that will be stored in Supabase user metadata
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'university', 'major', 'year_of_study', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself'
            }),
            'university': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your university'
            }),
            'major': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your major/field of study'
            }),
            'year_of_study': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 8,
                'placeholder': 'Year of study'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Accept Supabase user data
        supabase_user = kwargs.pop('supabase_user', None)
        super().__init__(*args, **kwargs)
        
        if supabase_user:
            metadata = getattr(supabase_user, 'supabase_data', {}).get('user_metadata', {})
            self.fields['first_name'].initial = metadata.get('first_name', '')
            self.fields['last_name'].initial = metadata.get('last_name', '')
    
    def save_supabase_metadata(self, supabase_user):
        """Save first_name and last_name to Supabase user metadata"""
        try:
            supabase_client = get_supabase_client()
            if supabase_client.is_available():
                # Update user metadata in Supabase
                response = supabase_client.client.auth.update_user({
                    'data': {
                        'first_name': self.cleaned_data.get('first_name', ''),
                        'last_name': self.cleaned_data.get('last_name', ''),
                    }
                })
                logger.info(f"Updated Supabase user metadata: {supabase_user.email}")
        except Exception as e:
            logger.error(f"Failed to update Supabase user metadata: {str(e)}")
