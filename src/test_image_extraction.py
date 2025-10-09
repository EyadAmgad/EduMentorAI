import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rag_django.settings')
django.setup()

from rag_app.models import Document, DocumentImage
from rag_app.pipeline.data_processor import DocumentProcessor
import logging

# Enable detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get a recent PDF document
recent_pdf = Document.objects.filter(document_type='pdf').order_by('-uploaded_at').first()

if recent_pdf:
    print(f"\n{'='*60}")
    print(f"Testing image extraction on: {recent_pdf.title}")
    print(f"Uploaded: {recent_pdf.uploaded_at}")
    print(f"File exists: {os.path.exists(recent_pdf.file.path)}")
    print(f"{'='*60}\n")
    
    # Check current images
    current_images = DocumentImage.objects.filter(document=recent_pdf).count()
    print(f"Current images in DB: {current_images}")
    
    # Try to extract images
    print("\nAttempting to extract images...")
    processor = DocumentProcessor()
    
    try:
        images = processor._extract_and_save_images_with_ocr(recent_pdf)
        print(f"\n✅ Successfully extracted {len(images)} images!")
        
        for img in images[:3]:  # Show first 3
            print(f"  - Page {img.page_number}, Image {img.image_index}: {len(img.ocr_text) if img.ocr_text else 0} OCR chars")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check final count
    final_images = DocumentImage.objects.filter(document=recent_pdf).count()
    print(f"\nFinal images in DB: {final_images}")
    
else:
    print("No PDF documents found")
