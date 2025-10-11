#!/usr/bin/env python
"""
Test script for NEW image search workflow
Tests: Generate slides -> Extract queries -> Search images -> Match to slides
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.pipeline.SlideProcessor import SlideProcessor

def test_new_workflow():
    """Test the new image search workflow"""
    print("=" * 70)
    print("Testing NEW Image Search Workflow")
    print("=" * 70)
    
    # Initialize SlideProcessor
    processor = SlideProcessor()
    
    # Test slide content (simulating generated slides)
    test_slide_content = """
### Introduction to Machine Learning
• Machine Learning is a subset of AI
• It enables computers to learn from data
• Applications include image recognition and NLP

### Supervised Learning
• Labeled training data is required
• Algorithms learn mapping from inputs to outputs
• Examples: Classification and Regression

### Neural Networks
• Inspired by biological neurons
• Multiple layers process information
• Deep learning uses many layers

### Applications and Future
• Healthcare diagnosis
• Autonomous vehicles
• Natural language processing
"""
    
    print("\n📄 Sample Slide Content:")
    print("-" * 70)
    print(test_slide_content[:200] + "...\n")
    
    # Step 1: Extract slide titles
    print("\n1️⃣ Extracting slide titles...")
    print("-" * 70)
    slide_titles = processor._extract_slide_titles(test_slide_content)
    print(f"✅ Found {len(slide_titles)} slide titles:")
    for i, title in enumerate(slide_titles, 1):
        print(f"   {i}. {title}")
    
    # Step 2: Generate search queries
    print("\n2️⃣ Generating search queries from slides...")
    print("-" * 70)
    search_queries = processor._generate_search_queries_from_slides(slide_titles, max_queries=3)
    print(f"✅ Generated {len(search_queries)} search queries:")
    for i, query in enumerate(search_queries, 1):
        print(f"   {i}. '{query}'")
    
    # Step 3: Search for images
    print("\n3️⃣ Searching for images...")
    print("-" * 70)
    all_images = []
    for query in search_queries:
        print(f"\n🔍 Searching for: '{query}'")
        images = processor._search_and_download_images(query, num_images=1)
        all_images.extend(images)
        if images:
            print(f"   ✅ Downloaded {len(images)} image(s)")
        else:
            print(f"   ⚠️ No images found")
    
    print(f"\n✅ Total images downloaded: {len(all_images)}")
    
    # Step 4: Match images to slides
    print("\n4️⃣ Matching images to slides...")
    print("-" * 70)
    image_placements = processor._match_images_to_slides(test_slide_content, all_images)
    print(f"✅ Created {len(image_placements)} image placements:")
    for placement in image_placements:
        slide_idx = placement['slide_index']
        img = placement['image']
        print(f"   - Slide {slide_idx}: Image about '{img['ocr_text']}'")
    
    # Step 5: Verify files exist
    print("\n5️⃣ Verifying downloaded images...")
    print("-" * 70)
    for i, img in enumerate(all_images, 1):
        if os.path.exists(img['image_path']):
            file_size = os.path.getsize(img['image_path']) / 1024  # KB
            print(f"   ✅ Image {i}: {img['ocr_text']} ({file_size:.1f} KB)")
        else:
            print(f"   ❌ Image {i}: NOT FOUND")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 WORKFLOW TEST SUMMARY")
    print("=" * 70)
    print(f"✅ Slides extracted: {len(slide_titles)}")
    print(f"✅ Search queries generated: {len(search_queries)}")
    print(f"✅ Images downloaded: {len(all_images)}")
    print(f"✅ Images matched to slides: {len(image_placements)}")
    
    if len(all_images) == 3 and len(image_placements) == 3:
        print("\n🎉 SUCCESS! New workflow is working perfectly!")
        print("\n✨ How it works:")
        print("   1. Generate slide content (titles + bullets)")
        print("   2. Extract slide titles")
        print("   3. Generate search queries from titles")
        print("   4. Search for 1 image per query (3 total)")
        print("   5. Match images to appropriate slides")
        print("   6. Create PowerPoint with images on right, text on left")
    else:
        print("\n⚠️ PARTIAL SUCCESS - Some issues detected")
        print(f"   Expected 3 images, got {len(all_images)}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    test_new_workflow()
