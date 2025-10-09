#!/usr/bin/env python
"""
Script to check for images and re-process documents if needed
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.models import DocumentImage, Document
from rag_app.pipeline.data_processor import DocumentProcessor
from django.contrib.auth.models import User

def main():
    print("="*60)
    print("CHECKING DOCUMENT IMAGES STATUS")
    print("="*60)
    
    # Check total images
    total_images = DocumentImage.objects.count()
    print(f"\n📊 Total images in database: {total_images}")
    
    # Check OCR processed images
    ocr_images = DocumentImage.objects.filter(ocr_processed=True).count()
    print(f"📊 Images with OCR: {ocr_images}")
    
    # Check PDF documents
    pdf_docs = Document.objects.filter(document_type='pdf', processed=True)
    print(f"\n📄 Total PDF documents: {pdf_docs.count()}")
    
    # Check which PDFs have images
    docs_with_images = 0
    docs_without_images = []
    
    for doc in pdf_docs:
        img_count = DocumentImage.objects.filter(document=doc).count()
        if img_count > 0:
            docs_with_images += 1
            print(f"  ✓ '{doc.title}': {img_count} images")
        else:
            docs_without_images.append(doc)
            print(f"  ✗ '{doc.title}': NO IMAGES")
    
    print(f"\n📊 Summary:")
    print(f"  - PDFs with images: {docs_with_images}")
    print(f"  - PDFs WITHOUT images: {len(docs_without_images)}")
    
    # Offer to re-process
    if docs_without_images:
        print("\n" + "="*60)
        print("FIXING DOCUMENTS WITHOUT IMAGES")
        print("="*60)
        
        response = input(f"\nDo you want to extract images from {len(docs_without_images)} PDF(s)? (yes/no): ")
        
        if response.lower() in ['yes', 'y']:
            processor = DocumentProcessor()
            
            for doc in docs_without_images:
                print(f"\n🔄 Processing '{doc.title}'...")
                try:
                    images = processor._extract_and_save_images_with_ocr(doc)
                    if images:
                        print(f"  ✓ Extracted {len(images)} images with OCR")
                    else:
                        print(f"  ⚠ No images found in this PDF")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
            
            # Final check
            print("\n" + "="*60)
            print("FINAL STATUS")
            print("="*60)
            total_images_after = DocumentImage.objects.count()
            print(f"Total images now: {total_images_after} (was: {total_images})")
            print(f"New images extracted: {total_images_after - total_images}")
        else:
            print("\nℹ️  Skipped re-processing")
    else:
        print("\n✅ All PDF documents have images extracted!")
    
    # Show sample
    sample_img = DocumentImage.objects.filter(ocr_processed=True).first()
    if sample_img:
        print("\n" + "="*60)
        print("SAMPLE IMAGE")
        print("="*60)
        print(f"Document: {sample_img.document.title}")
        print(f"Page: {sample_img.page_number}")
        print(f"OCR text (first 100 chars): {sample_img.ocr_text[:100] if sample_img.ocr_text else 'None'}")
        print(f"Image file: {sample_img.image_file.name if sample_img.image_file else 'None'}")
        if sample_img.image_file:
            print(f"File exists: {os.path.exists(sample_img.image_file.path)}")

if __name__ == '__main__':
    main()
