"""
Pytest configuration and fixtures for EduMentorAI tests
"""
import pytest
import os
import tempfile
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rag_app.models import Subject, Document, ChatSession


User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def user(db):
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def subject(db):
    """Create a test subject"""
    return Subject.objects.create(
        name='Test Subject',
        description='A test subject for testing purposes'
    )


@pytest.fixture
def document(db, user, subject):
    """Create a test document"""
    # Create a mock file
    file_content = b"This is test content for the document."
    uploaded_file = SimpleUploadedFile(
        "test_document.pdf",
        file_content,
        content_type="application/pdf"
    )
    
    return Document.objects.create(
        title='Test Document',
        subject=subject,
        uploaded_by=user,
        file=uploaded_file,
        file_type='pdf'
    )


@pytest.fixture
def chat_session(db, user, subject, document):
    """Create a test chat session"""
    return ChatSession.objects.create(
        user=user,
        subject=subject,
        document=document,
        title='Test Chat Session'
    )


@pytest.fixture
def multiple_documents(db, user, subject):
    """Create multiple test documents"""
    documents = []
    for i in range(3):
        file_content = f"This is test content for document {i+1}.".encode()
        uploaded_file = SimpleUploadedFile(
            f"test_document_{i+1}.pdf",
            file_content,
            content_type="application/pdf"
        )
        
        doc = Document.objects.create(
            title=f'Test Document {i+1}',
            subject=subject,
            uploaded_by=user,
            file=uploaded_file,
            file_type='pdf'
        )
        documents.append(doc)
    
    return documents


@pytest.fixture
def pdf_file():
    """Create a mock PDF file for testing"""
    content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<<\n/Size 1\n/Root 1 0 R\n>>\nstartxref\n9\n%%EOF'
    return SimpleUploadedFile(
        "test.pdf",
        content,
        content_type="application/pdf"
    )


@pytest.fixture
def txt_file():
    """Create a text file for testing"""
    content = "This is test content for the text file."
    return SimpleUploadedFile(
        "test.txt",
        content.encode('utf-8'),
        content_type="text/plain"
    )


@pytest.fixture
def docx_file():
    """Create a mock DOCX file for testing"""
    # Simplified mock DOCX content
    content = b'PK\x03\x04\x14\x00\x00\x00\x08\x00'
    return SimpleUploadedFile(
        "test.docx",
        content,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@pytest.fixture
def temp_media_root():
    """Create a temporary media root for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            yield temp_dir


@pytest.fixture
def mock_embedding():
    """Create a mock embedding vector"""
    import random
    return [random.uniform(-1, 1) for _ in range(384)]


@pytest.fixture
def mock_vectorstore(monkeypatch):
    """Mock the vectorstore for testing"""
    class MockVectorStore:
        def __init__(self):
            self.documents = []
            
        def add_texts(self, texts, metadatas=None, ids=None):
            for i, text in enumerate(texts):
                self.documents.append({
                    'content': text,
                    'metadata': metadatas[i] if metadatas else {},
                    'id': ids[i] if ids else str(i)
                })
                
        def similarity_search(self, query, k=4):
            # Return mock search results
            return [
                {
                    'content': f'Mock result {i+1} for query: {query}',
                    'metadata': {'chunk_id': f'chunk_{i+1}', 'document_id': 1}
                }
                for i in range(min(k, len(self.documents)))
            ]
            
        def delete(self, ids):
            self.documents = [doc for doc in self.documents if doc['id'] not in ids]
    
    mock_store = MockVectorStore()
    
    def mock_get_vectorstore():
        return mock_store
    
    monkeypatch.setattr('rag_app.pipeline.vectorstore.get_vectorstore', mock_get_vectorstore)
    return mock_store


@pytest.fixture
def mock_llm_response(monkeypatch):
    """Mock LLM response for testing"""
    def mock_generate_response(query, context):
        return {
            'response': f'Mock AI response for query: {query}',
            'confidence': 0.85,
            'sources': ['chunk_1', 'chunk_2']
        }
    
    monkeypatch.setattr('rag_app.pipeline.model.generate_response', mock_generate_response)
    return mock_generate_response


@pytest.fixture
def mock_embeddings(monkeypatch):
    """Mock embeddings model for testing"""
    class MockEmbeddings:
        def embed_documents(self, texts):
            return [[0.1, 0.2, 0.3] * 128 for _ in texts]  # 384-dim embeddings
            
        def embed_query(self, text):
            return [0.1, 0.2, 0.3] * 128  # 384-dim embedding
    
    mock_embeddings = MockEmbeddings()
    
    def mock_get_embeddings():
        return mock_embeddings
    
    monkeypatch.setattr('rag_app.pipeline.embeddings.get_embeddings', mock_get_embeddings)
    return mock_embeddings


@pytest.fixture
def client_logged_in(client, user):
    """Client with logged in user"""
    client.force_login(user)
    return client


@pytest.fixture
def api_client():
    """API client for testing"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def api_client_logged_in(api_client, user):
    """API client with logged in user"""
    api_client.force_authenticate(user=user)
    return api_client


# Pytest markers configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "external: marks tests that require external services"
    )


# Custom test collection
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location"""
    for item in items:
        # Add markers based on test file names
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker for tests with 'slow' in name
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
