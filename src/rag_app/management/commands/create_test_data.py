"""
Django management command for creating test data and fixtures.

Usage:
    python manage.py create_test_data
    python manage.py create_test_data --users 10 --subjects 5
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rag_app.models import Subject, Document, ChatSession, DocumentChunk


User = get_user_model()


class Command(BaseCommand):
    help = 'Create test data for development and testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of test users to create (default: 5)'
        )
        parser.add_argument(
            '--subjects',
            type=int,
            default=3,
            help='Number of test subjects to create (default: 3)'
        )
        parser.add_argument(
            '--documents',
            type=int,
            default=10,
            help='Number of test documents to create (default: 10)'
        )
        parser.add_argument(
            '--chat-sessions',
            type=int,
            default=15,
            help='Number of test chat sessions to create (default: 15)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing test data before creating new data'
        )

    def handle(self, *args, **options):
        """Main command handler"""
        self.stdout.write(
            self.style.SUCCESS('🏗️ Creating test data for EduMentorAI...')
        )
        
        if options['clear_existing']:
            self._clear_existing_data()
        
        # Create test data
        users = self._create_test_users(options['users'])
        subjects = self._create_test_subjects(options['subjects'])
        documents = self._create_test_documents(options['documents'], users, subjects)
        chat_sessions = self._create_test_chat_sessions(options['chat_sessions'], users, subjects, documents)
        
        # Print summary
        self._print_summary(users, subjects, documents, chat_sessions)
        
        self.stdout.write(
            self.style.SUCCESS('\n✅ Test data creation complete!')
        )

    def _clear_existing_data(self):
        """Clear existing test data"""
        self.stdout.write('🗑️ Clearing existing test data...')
        
        # Delete in reverse dependency order
        ChatSession.objects.all().delete()
        DocumentChunk.objects.all().delete()
        Document.objects.all().delete()
        Subject.objects.all().delete()
        
        # Keep superusers but delete regular test users
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write('  ✓ Existing test data cleared')

    def _create_test_users(self, count):
        """Create test users"""
        self.stdout.write(f'👥 Creating {count} test users...')
        
        users = []
        for i in range(count):
            username = f'testuser{i+1}'
            email = f'testuser{i+1}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Test',
                    'last_name': f'User {i+1}',
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('testpass123')
                user.save()
            
            users.append(user)
        
        self.stdout.write(f'  ✓ Created {len(users)} users')
        return users

    def _create_test_subjects(self, count):
        """Create test subjects"""
        self.stdout.write(f'📚 Creating {count} test subjects...')
        
        subject_names = [
            'Computer Science', 'Mathematics', 'Physics', 'Chemistry',
            'Biology', 'History', 'Literature', 'Psychology',
            'Economics', 'Engineering', 'Medicine', 'Law'
        ]
        
        # Get or create a default user for subjects
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        
        subjects = []
        for i in range(count):
            name = subject_names[i % len(subject_names)]
            code = f'CS{100 + i}'  # Generate course codes like CS100, CS101, etc.
            
            if i >= len(subject_names):
                name = f'{name} {i // len(subject_names) + 1}'
                code = f'CS{100 + i}'
            
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': f'Test subject for {name} with comprehensive course materials and resources.',
                    'created_by': admin_user
                }
            )
            
            subjects.append(subject)
        
        self.stdout.write(f'  ✓ Created {len(subjects)} subjects')
        return subjects

    def _create_test_documents(self, count, users, subjects):
        """Create test documents"""
        self.stdout.write(f'📄 Creating {count} test documents...')
        
        document_types = ['pdf', 'txt', 'docx', 'pptx']
        document_titles = [
            'Introduction to Programming', 'Advanced Mathematics',
            'Physics Fundamentals', 'Chemistry Lab Manual',
            'Biology Textbook', 'World History Overview',
            'Literature Analysis', 'Psychology Principles',
            'Economic Theory', 'Engineering Handbook',
            'Medical Terminology', 'Legal Studies'
        ]
        
        documents = []
        for i in range(count):
            title = document_titles[i % len(document_titles)]
            if i >= len(document_titles):
                title = f'{title} - Part {i // len(document_titles) + 1}'
            
            file_type = random.choice(document_types)
            content = self._generate_test_content(title, file_type)
            
            uploaded_file = SimpleUploadedFile(
                f'test_document_{i+1}.{file_type}',
                content,
                content_type=self._get_content_type(file_type)
            )
            
            document = Document.objects.create(
                title=title,
                subject=random.choice(subjects),
                uploaded_by=random.choice(users),
                file=uploaded_file,
                document_type=file_type,
                file_size=len(content),  # Set file size
                processed=True,
                page_count=random.randint(1, 50)  # Random page count
            )
            
            # Create some document chunks
            self._create_document_chunks(document)
            
            documents.append(document)
        
        self.stdout.write(f'  ✓ Created {len(documents)} documents')
        return documents

    def _create_test_chat_sessions(self, count, users, subjects, documents):
        """Create test chat sessions"""
        self.stdout.write(f'💬 Creating {count} test chat sessions...')
        
        chat_titles = [
            'General Discussion', 'Homework Help', 'Exam Preparation',
            'Project Research', 'Concept Clarification', 'Study Group',
            'Assignment Questions', 'Review Session', 'Lab Discussion',
            'Thesis Help', 'Quiz Preparation', 'Course Overview'
        ]
        
        chat_sessions = []
        for i in range(count):
            title = chat_titles[i % len(chat_titles)]
            if i >= len(chat_titles):
                title = f'{title} {i // len(chat_titles) + 1}'
            
            chat_session = ChatSession.objects.create(
                user=random.choice(users),
                subject=random.choice(subjects),
                document=random.choice(documents) if random.choice([True, False]) else None,
                title=title,
                created_at=self._get_random_datetime()
            )
            
            chat_sessions.append(chat_session)
        
        self.stdout.write(f'  ✓ Created {len(chat_sessions)} chat sessions')
        return chat_sessions

    def _create_document_chunks(self, document):
        """Create document chunks for a document"""
        chunk_count = random.randint(3, 8)
        
        for i in range(chunk_count):
            DocumentChunk.objects.create(
                document=document,
                chunk_index=i,
                content=f'This is chunk {i+1} of document "{document.title}". It contains relevant information about the topic and can be used for retrieval-augmented generation. This chunk discusses important concepts and provides detailed explanations that would be useful for students learning about the subject matter.',
                page_number=i+1  # Add page number
            )

    def _generate_test_content(self, title, file_type):
        """Generate test content based on file type"""
        base_content = f'Test content for {title}. This document contains educational material for testing purposes.'
        
        if file_type == 'pdf':
            # Mock PDF header
            return b'%PDF-1.4\n' + base_content.encode('utf-8')
        elif file_type == 'txt':
            return base_content.encode('utf-8')
        elif file_type == 'docx':
            # Mock DOCX (ZIP) header
            return b'PK\x03\x04' + base_content.encode('utf-8')
        elif file_type == 'pptx':
            # Mock PPTX (ZIP) header
            return b'PK\x03\x04' + base_content.encode('utf-8')
        else:
            return base_content.encode('utf-8')

    def _get_content_type(self, file_type):
        """Get content type for file type"""
        content_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        }
        return content_types.get(file_type, 'application/octet-stream')

    def _get_random_datetime(self):
        """Get a random datetime for testing"""
        from django.utils import timezone
        import datetime
        
        now = timezone.now()
        days_ago = random.randint(1, 30)
        return now - datetime.timedelta(days=days_ago)

    def _print_summary(self, users, subjects, documents, chat_sessions):
        """Print summary of created test data"""
        self.stdout.write(
            self.style.HTTP_INFO('\n📊 Test Data Summary:')
        )
        
        summary_items = [
            f'Users: {len(users)}',
            f'Subjects: {len(subjects)}',
            f'Documents: {len(documents)}',
            f'Chat Sessions: {len(chat_sessions)}',
            f'Document Chunks: {DocumentChunk.objects.count()}'
        ]
        
        for item in summary_items:
            self.stdout.write(f'  • {item}')
        
        self.stdout.write(
            self.style.HTTP_INFO('\n🔑 Test User Credentials:')
        )
        self.stdout.write('  • Username: testuser1, Password: testpass123')
        self.stdout.write('  • Username: testuser2, Password: testpass123')
        self.stdout.write('  • ... (and so on for all test users)')
        
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('\n  • Admin: admin, Password: admin123 (if created)')
