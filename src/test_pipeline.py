#!/usr/bin/env python
"""
Test script to verify the RAG pipeline is working correctly
"""
import os
import sys
import django

# Add the Django project directory to the Python path
sys.path.append('/home/ziadtarek-new/EduMentorAI/src')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

def test_imports():
    """Test if all pipeline modules can be imported"""
    print("Testing imports...")
    
    try:
        from rag_app.pipeline.data_processor import DocumentProcessor
        print("✓ DocumentProcessor imported successfully")
    except Exception as e:
        print(f"✗ DocumentProcessor import failed: {e}")
        return False
    
    try:
        from rag_app.pipeline.vectorstore import VectorStore
        print("✓ VectorStore imported successfully")
    except Exception as e:
        print(f"✗ VectorStore import failed: {e}")
        return False
    
    try:
        from rag_app.pipeline.retriever import DocumentRetriever
        print("✓ DocumentRetriever imported successfully")
    except Exception as e:
        print(f"✗ DocumentRetriever import failed: {e}")
        return False
    
    try:
        from rag_app.pipeline.model import RAGModel, get_rag_model
        print("✓ RAGModel imported successfully")
    except Exception as e:
        print(f"✗ RAGModel import failed: {e}")
        return False
    
    return True

def test_document_processor():
    """Test DocumentProcessor initialization"""
    print("\nTesting DocumentProcessor...")
    
    try:
        from rag_app.pipeline.data_processor import DocumentProcessor
        processor = DocumentProcessor()
        print("✓ DocumentProcessor initialized successfully")
        return True
    except Exception as e:
        print(f"✗ DocumentProcessor initialization failed: {e}")
        return False

def test_rag_model():
    """Test RAG model initialization"""
    print("\nTesting RAG model...")
    
    try:
        from rag_app.pipeline.model import get_rag_model
        rag_model = get_rag_model()
        print("✓ RAG model initialized successfully")
        return True
    except Exception as e:
        print(f"✗ RAG model initialization failed: {e}")
        return False

def test_database_connection():
    """Test database models"""
    print("\nTesting database models...")
    
    try:
        from rag_app.models import Subject, Document, DocumentChunk, ChatSession
        
        # Test basic queries
        subject_count = Subject.objects.count()
        document_count = Document.objects.count()
        chunk_count = DocumentChunk.objects.count()
        session_count = ChatSession.objects.count()
        
        print(f"✓ Database connected successfully")
        print(f"  - Subjects: {subject_count}")
        print(f"  - Documents: {document_count}")
        print(f"  - Document chunks: {chunk_count}")
        print(f"  - Chat sessions: {session_count}")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing RAG Pipeline Integration")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("DocumentProcessor Test", test_document_processor),
        ("RAG Model Test", test_rag_model),
        ("Database Test", test_database_connection),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n[{test_name}]")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with error: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! RAG pipeline is ready.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
