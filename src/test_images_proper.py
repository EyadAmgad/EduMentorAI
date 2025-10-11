#!/usr/bin/env python3
"""
Proper test script for image search functionality with Django settings configured
"""

# Configure Django settings FIRST before any imports
import os
import sys
import django

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')

# Initialize Django
django.setup()

# NOW we can import Django-dependent modules
from rag_app.pipeline.SlideProcessor import SlideProcessor

def test_image_search():
    """Test the image search functionality"""
    print("=" * 60)
    print("Testing Image Search with Django Configured")
    print("=" * 60)
    
    processor = SlideProcessor()
    
    # Test 1: Search and download images
    print("\n1. Testing image search and download...")
    try:
        images = processor._search_and_download_images(
            query='Machine Learning',
            num_images=1,
            slide_index=1
        )
        if images:
            print(f"✅ Downloaded {len(images)} image(s)")
            for img in images:
                print(f"   Slide index: {img['slide_index']}")
                print(f"   Image path: {img['image_path']}")
                print(f"   Dimensions: {img['width']}x{img['height']}")
                print(f"   Source: {img['source']}")
                # Check file size
                if os.path.exists(img['image_path']):
                    file_size = os.path.getsize(img['image_path']) / 1024
                    print(f"   File size: {file_size:.1f} KB")
        else:
            print("❌ No images downloaded")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 2: Extract slide titles
    print("\n2. Testing title extraction...")
    test_content = """### Machine Learning Basics
Some content here

### Neural Networks
More content

### Deep Learning
Final content"""
    
    try:
        titles = processor._extract_slide_titles(test_content)
        print(f"✅ Extracted titles: {titles}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 3: Check if module loaded correctly
    print("\n3. Checking module status...")
    if processor.llm_available:
        print("✅ RAG model available")
    else:
        print("⚠️  RAG model not available (this is OK for testing)")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_image_search()
