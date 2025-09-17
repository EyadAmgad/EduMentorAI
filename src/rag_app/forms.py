"""
Django forms for EduMentorAI
"""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.core.exceptions import ValidationError
import logging
from .models import Subject, Document, Quiz, UserProfile, ChatMessage
from .supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


class SupabaseSignUpForm(UserCreationForm):
    """Custom signup form that works with Supabase"""
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
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field
        if 'username' in self.fields:
            del self.fields['username']
        
        # Update password field styles
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter password',
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'autocomplete': 'new-password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Use email as username
        user.is_active = False  # Set to False until email is verified
        
        if commit:
            user.save()
            
            # Create user in Supabase and send verification email
            try:
                supabase_client = get_supabase_client()
                if supabase_client.is_available():
                    response = supabase_client.create_user(
                        email=user.email,
                        password=self.cleaned_data['password1'],
                        email_confirm=True,  # This triggers email verification
                        data={
                            'first_name': self.cleaned_data.get('first_name', ''),
                            'last_name': self.cleaned_data.get('last_name', ''),
                        }
                    )
                    logger.info(f"User created in Supabase with email verification: {user.email}")
                else:
                    # Fallback: activate user immediately if Supabase is not available
                    user.is_active = True
                    user.save()
                    logger.warning("Supabase not available, activating user immediately")
            except Exception as e:
                # If Supabase creation fails, still keep Django user but activate them
                logger.warning(f"Failed to create user in Supabase: {str(e)}")
                user.is_active = True
                user.save()
        
        return user


class SupabaseLoginForm(AuthenticationForm):
    """Custom login form that works with Supabase"""
    username = forms.EmailField(
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
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Check if user exists and is active
            try:
                user = User.objects.get(email=username)
                if not user.is_active:
                    raise ValidationError(
                        "Your account is not yet verified. Please check your email for a verification link, "
                        "or request a new verification email."
                    )
                
                # Try to authenticate with Supabase first
                try:
                    supabase_client = get_supabase_client()
                    if supabase_client.is_available():
                        response = supabase_client.sign_in_user(username, password)
                        
                        if response and 'user' in response:
                            # Check if email is verified in Supabase
                            if not response['user'].get('email_confirmed_at'):
                                raise ValidationError(
                                    "Please verify your email address before logging in. "
                                    "Check your inbox for a verification link."
                                )
                            
                            # Update Django user if needed
                            if user.check_password(password):
                                self.user_cache = user
                            else:
                                # Update Django password to match Supabase
                                user.set_password(password)
                                user.save()
                                self.user_cache = user
                        else:
                            raise ValidationError("Invalid email or password.")
                    else:
                        # Fallback to Django authentication
                        if user.check_password(password):
                            self.user_cache = user
                        else:
                            raise ValidationError("Invalid email or password.")
                except Exception as e:
                    logger.warning(f"Supabase authentication failed: {str(e)}")
                    # Fallback to Django authentication
                    if user.check_password(password):
                        self.user_cache = user
                    else:
                        raise ValidationError("Invalid email or password.")
                        
            except User.DoesNotExist:
                raise ValidationError("Invalid email or password.")
        
        return self.cleaned_data


class SupabasePasswordResetForm(PasswordResetForm):
    """Custom password reset form that works with Supabase"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """Override to use Supabase for password reset"""
        try:
            supabase_client = get_supabase_client()
            if supabase_client.is_available():
                # Use Supabase password reset
                response = supabase_client.client.auth.reset_password_email(to_email)
                return
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send reset email via Supabase: {str(e)}")
        
        # Fallback to Django email
        super().send_mail(
            subject_template_name, email_template_name, context, 
            from_email, to_email, html_email_template_name
        )


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
    
    class Meta:
        model = Document
        fields = ['title', 'file', 'subject']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter document title'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx,.txt,.pptx'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(created_by=user)
        
        # Add help text
        self.fields['file'].help_text = 'Supported formats: PDF, DOCX, TXT, PPTX (Max 10MB)'
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 10MB')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.docx', '.txt', '.pptx']
            file_extension = '.' + file.name.split('.')[-1].lower()
            
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    'File type not supported. Please upload PDF, DOCX, TXT, or PPTX files.'
                )
        
        return file


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


class ProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    
    # Add user fields
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
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
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
        super().__init__(*args, **kwargs)
        
        # Populate user fields if instance exists
        if self.instance and self.instance.user:
            user = self.instance.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if commit:
            # Update user fields
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
            
            profile.save()
        
        return profile


class ChatMessageForm(forms.ModelForm):
    """Form for chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ask a question about your uploaded materials...',
                'style': 'resize: none;'
            })
        }


class QuizQuestionForm(forms.Form):
    """Dynamic form for quiz questions"""
    
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)
        
        for question in questions:
            field_name = f'question_{question.id}'
            
            if question.question_type == 'mcq':
                choices = [(choice.id, choice.choice_text) for choice in question.choices.all()]
                self.fields[field_name] = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    required=True,
                    label=question.question_text
                )
            
            elif question.question_type == 'tf':
                self.fields[field_name] = forms.ChoiceField(
                    choices=[('True', 'True'), ('False', 'False')],
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    required=True,
                    label=question.question_text
                )
            
            elif question.question_type in ['sa', 'fb']:
                self.fields[field_name] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 3,
                        'placeholder': 'Enter your answer...'
                    }),
                    required=True,
                    label=question.question_text
                )


class SearchForm(forms.Form):
    """Form for searching documents"""
    
    query = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search your documents...',
            'autocomplete': 'off'
        })
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        required=False,
        empty_label="All subjects",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(created_by=user)


class SlideGenerationForm(forms.Form):
    """Form for generating slides"""
    
    document = forms.ModelChoiceField(
        queryset=Document.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select a document to generate slides from"
    )
    
    topic = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Specific topic or leave empty for full document'
        }),
        help_text="Optional: Specify a particular topic to focus on"
    )
    
    slide_count = forms.IntegerField(
        min_value=3,
        max_value=20,
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 3,
            'max': 20
        }),
        help_text="Number of slides to generate (3-20)"
    )
    
    include_images = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Include placeholder for images in slides"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['document'].queryset = Document.objects.filter(
                uploaded_by=user, processed=True
            )


class BulkDocumentUploadForm(forms.Form):
    """Form for bulk document upload"""
    
    files = MultipleFileField(
        help_text="Select multiple files to upload at once"
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(created_by=user)


class UserProfileForm(forms.ModelForm):
    """Form for user profile management"""
    
    # Add user fields that can be edited
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
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address',
            'readonly': True  # Email changes should go through AllAuth
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ['bio', 'university', 'major', 'year_of_study', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'university': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'University or Institution'
            }),
            'major': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Major or Field of Study'
            }),
            'year_of_study': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year of Study (e.g., 1, 2, 3, 4)',
                'min': 1,
                'max': 10
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if self.user:
            # Update user fields
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            if commit:
                self.user.save()
            
            profile.user = self.user
        
        if commit:
            profile.save()
        
        return profile
