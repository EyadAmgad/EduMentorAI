#!/usr/bin/env python
"""
Test script for internet image search functionality
Run this to verify SerpApi integration is working correctly
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.pipeline.SlideProcessor import SlideProcessor

def test_image_search():
    """Test the image search functionality"""
    print("=" * 60)
    print("Testing Internet Image Search")
    print("=" * 60)
    
    # Initialize SlideProcessor
    processor = SlideProcessor()
    
    # Test query
    test_query = "Machine Learning"
    print(f"\n🔍 Testing image search with query: '{test_query}'")
    print("-" * 60)
    
    # Search for images
    images = processor._search_and_download_images(test_query, num_images=3)
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: Found {len(images)} images")
    print("=" * 60)
    
    if images:
        print("\n✅ Image search is working!")
        for i, img in enumerate(images, 1):
            print(f"\nImage {i}:")
            print(f"  - Path: {img['image_path']}")
            print(f"  - Size: {img['width']}x{img['height']}")
            print(f"  - Source: {img['source']}")
            print(f"  - Description: {img['ocr_text']}")
            
        # Check if files actually exist
        print("\n🔍 Verifying files exist...")
        for i, img in enumerate(images, 1):
            if os.path.exists(img['image_path']):
                file_size = os.path.getsize(img['image_path']) / 1024  # KB
                print(f"  ✓ Image {i} exists ({file_size:.1f} KB)")
            else:
                print(f"  ✗ Image {i} NOT found")
    else:
        print("\n❌ No images found. Possible issues:")
        print("  1. Check if SERPAPI_KEY is set in .env file")
        print("  2. Verify internet connection")
        print("  3. Check SerpApi account has remaining credits")
        print("  4. Review the logs above for specific errors")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_image_search()
