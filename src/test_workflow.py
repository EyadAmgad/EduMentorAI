#!/usr/bin/env python3
"""
Test the complete image placement workflow
"""

import os
import sys
import django

# Configure Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.pipeline.SlideProcessor import SlideProcessor

def test_workflow():
    """Test the complete image → slide matching workflow"""
    print("=" * 60)
    print("Testing Complete Image Placement Workflow")
    print("=" * 60)
    
    processor = SlideProcessor()
    
    # Simulate generated slide content (as it would be from LLM)
    slide_content = """### Introduction to Machine Learning
• Machine Learning is a subset of AI
• Enables computers to learn from data
• Widely used in modern applications

### Neural Networks
• Inspired by biological neurons
• Consists of interconnected layers
• Foundation of deep learning

### Deep Learning Applications
• Computer vision and image recognition
• Natural language processing
• Autonomous vehicles"""

    print("\n1. Extract slide titles:")
    titles = processor._extract_slide_titles(slide_content)
    print(f"   Found {len(titles)} titles: {titles}")
    
    print("\n2. Calculate middle slides:")
    total_slides = len(titles)
    if total_slides >= 5:
        middle_idx = total_slides // 2
        target_slide_indices = [middle_idx - 1, middle_idx, middle_idx + 1]
    elif total_slides == 4:
        target_slide_indices = [1, 2]
    elif total_slides == 3:
        target_slide_indices = [1]
    else:
        target_slide_indices = []
    
    print(f"   Total slides: {total_slides}")
    print(f"   Target indices: {target_slide_indices}")
    print(f"   Target slides (1-indexed): {[i+1 for i in target_slide_indices]}")
    
    print("\n3. Download images:")
    internet_images = []
    for slide_idx in target_slide_indices:
        if slide_idx < len(titles):
            slide_title = titles[slide_idx]
            print(f"   Downloading for slide {slide_idx} (1-indexed: {slide_idx+1}): '{slide_title}'")
            
            # IMPORTANT: Match the real code - PowerPoint split creates empty first element
            # Title index 0 → PowerPoint slide index 1, etc.
            ppt_slide_index = slide_idx + 1
            
            # Search for 1 image
            images = processor._search_and_download_images(slide_title, num_images=1, slide_index=ppt_slide_index)
            if images:
                internet_images.extend(images)
                print(f"   ✓ Downloaded image with slide_index={images[0]['slide_index']}")
    
    print(f"\n   Total images downloaded: {len(internet_images)}")
    for img in internet_images:
        print(f"     - Image for slide_index {img['slide_index']} (1-indexed: {img['slide_index']+1})")
    
    print("\n4. Match images to slides:")
    placements = processor._match_images_to_slides(slide_content, internet_images)
    print(f"   Created {len(placements)} placements:")
    for p in placements:
        print(f"     - slide_index={p['slide_index']} (1-indexed: {p['slide_index']+1}), query='{p['image']['ocr_text']}'")
    
    print("\n5. Simulate PowerPoint creation:")
    slides = slide_content.split("###")
    for i, slide in enumerate(slides):
        if not slide.strip():
            continue
        
        lines = slide.strip().split("\n")
        slide_title = lines[0].strip()
        
        # Check for images (this is what the actual code does)
        slide_images = []
        for placement in placements:
            if placement['slide_index'] == i:
                slide_images.append(placement['image'])
        
        print(f"   Slide {i} (1-indexed: {i+1}): '{slide_title}'")
        if slide_images:
            print(f"     ✓ HAS IMAGE: {slide_images[0]['ocr_text']}")
        else:
            print(f"     ✗ NO IMAGE")
    
    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_workflow()
